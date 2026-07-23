"""Independent replication in a second treatment-outcome cohort (GSE67589).

Twenty pulmonary tuberculosis patients sampled at diagnosis, week 2 and week 4
on Affymetrix arrays, with outcome recorded as cure or relapse after apparently
successful therapy. The cohort is independent of the discovery data in patients,
country, platform and outcome definition, so agreement across it is a stringent
test of whether the immune axis holds rather than a repetition of the same
measurement.

Two questions are asked at each timepoint. Does the cell-composition axis
separate outcome groups in the same direction? And does a classifier trained
only on the discovery cohort assign higher risk to the patients who went on to
relapse? Because the platforms differ, transfer uses the rank-standardised
signature score rather than raw model coefficients.
"""
import json
import os
import urllib.request
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")

EXT = f"{C.ROOT}/external"
MATRIX = f"{EXT}/GSE67589_series_matrix.txt"
URL = ("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE67nnn/GSE67589/matrix/"
       "GSE67589_series_matrix.txt.gz")
TIMEPOINTS = ["Diagnosis", "Week 2", "Week 4"]
ARM_MAP = {"Diagnosis": "DX", "Week 2": "day_7", "Week 4": "week_4"}


def fetch():
    if os.path.exists(MATRIX):
        return
    import gzip
    print("downloading GSE67589 series matrix ...")
    with urllib.request.urlopen(URL, timeout=600) as r:
        raw = gzip.decompress(r.read()).decode("utf8", "ignore")
    with open(MATRIX, "w", encoding="utf8") as fh:
        fh.write(raw)


def load_external():
    """Return (expr indexed by gene symbol, sample table)."""
    fetch()
    with open(MATRIX, encoding="utf8") as fh:
        lines = fh.read().split("\n")

    def split(line):
        return [x.strip('"') for x in line.split("\t")[1:]]

    title = [l for l in lines if l.startswith("!Sample_title")][0]
    gsm = [l for l in lines if l.startswith("!Sample_geo_accession")][0]
    chars = [l for l in lines if l.startswith("!Sample_characteristics_ch1")]
    meta = pd.DataFrame({
        "gsm": split(gsm),
        "title": split(title),
        "timepoint": [x.split(":", 1)[1].strip() for x in split(chars[0])],
        "outcome": [x.split(":", 1)[1].strip() for x in split(chars[1])],
    })
    meta["patient"] = meta["title"].str.extract(r"Patient_(\w+?)_")
    meta["label"] = (meta["outcome"] == "Relapse").astype(int)

    start = [i for i, l in enumerate(lines)
             if l.startswith("!series_matrix_table_begin")][0]
    end = [i for i, l in enumerate(lines)
           if l.startswith("!series_matrix_table_end")][0]
    from io import StringIO
    tab = pd.read_csv(StringIO("\n".join(lines[start + 1:end])), sep="\t",
                      index_col=0)
    tab.index = [str(i).strip('"') for i in tab.index]
    tab.columns = [str(c).strip('"') for c in tab.columns]

    ann = probe_annotation(list(tab.index))
    tab = tab.loc[[p for p in tab.index if p in ann]]
    tab.index = [ann[p] for p in tab.index]
    tab = tab.groupby(level=0).max()          # one row per gene symbol
    return tab, meta.set_index("gsm")


def probe_annotation(probes):
    """Affymetrix HG-U133 Plus 2.0 probe -> gene symbol, from the GEO platform
    table (cached locally)."""
    cache = f"{EXT}/GPL570_probe_symbol.csv"
    if os.path.exists(cache):
        m = pd.read_csv(cache)
        return dict(zip(m["probe"].astype(str), m["symbol"].astype(str)))
    print("downloading GPL570 annotation ...")
    url = ("https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPLnnn/GPL570/annot/"
           "GPL570.annot.gz")
    import gzip
    with urllib.request.urlopen(url, timeout=900) as r:
        raw = gzip.decompress(r.read()).decode("utf8", "ignore")
    rows, started, sym_col = [], False, None
    for line in raw.split("\n"):
        if line.startswith("!platform_table_begin"):
            started = True
            continue
        if line.startswith("!platform_table_end"):
            break
        if not started:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if sym_col is None:
            # Header row: locate the gene-symbol column by name rather than
            # position, since annotation layouts differ between platforms.
            lowered = [p.lower() for p in parts]
            sym_col = (lowered.index("gene symbol")
                       if "gene symbol" in lowered else 2)
            continue
        if len(parts) > sym_col:
            sym = parts[sym_col]
            if sym and sym != "---":
                rows.append((parts[0], sym.split("///")[0].strip()))
    ann = pd.DataFrame(rows, columns=["probe", "symbol"])
    ann.to_csv(cache, index=False)
    return dict(zip(ann["probe"], ann["symbol"]))


def zscore_rows(df):
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1) + 1e-9, axis=0)


def signature_scores(expr_sym):
    """Marker-panel scores on the external platform, same panels as discovery."""
    z = zscore_rows(expr_sym)
    out, used = {}, {}
    for cell, genes in C.MARKERS.items():
        present = [g for g in genes if g in z.index]
        used[cell] = len(present)
        out[cell] = (z.loc[present].mean(axis=0) if present
                     else pd.Series(np.nan, index=z.columns))
    print("marker genes matched on the replication platform:", used)
    S = pd.DataFrame(out)
    S["NLR_score"] = S["Neutrophil"] - S["T_cell"]
    return S


def discovery_signature(arm, n_genes=60):
    """Directional gene weights learned on the discovery cohort only."""
    deg = pd.read_csv(f"{C.TAB}/deg_all_arms.csv")
    d = deg[deg.arm == arm].dropna(subset=["gene_symbol"])
    d = d[~d["gene_symbol"].astype(str).str.startswith("ENSG")]
    d = d.nsmallest(n_genes, "p_value")
    return dict(zip(d["gene_symbol"], np.sign(d["log2_fold_change"])))


def boot_auc_ci(labels, score, n=2000):
    """Bootstrap interval for the replication AUC. With fewer than twenty
    patients the interval is wide, and reporting it prevents a point estimate
    from being read as more than it is."""
    rng = np.random.default_rng(C.SEED)
    idx = np.arange(len(labels))
    vals = []
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if len(np.unique(labels[b])) < 2:
            continue
        vals.append(roc_auc_score(labels[b], score[b]))
    if not vals:
        return float("nan"), float("nan")
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def transfer_score(expr_sym, weights):
    z = zscore_rows(expr_sym)
    shared = [g for g in weights if g in z.index]
    if not shared:
        return None, 0
    w = np.array([weights[g] for g in shared])
    return (z.loc[shared].T.values @ w) / len(shared), len(shared)


def main():
    expr, meta = load_external()
    print(f"external cohort: {expr.shape[0]:,} gene symbols, "
          f"{expr.shape[1]} arrays, {meta['patient'].nunique()} patients")
    print(pd.crosstab(meta["timepoint"], meta["outcome"]))

    S = signature_scores(expr)
    rows, auc_rows = [], []

    for tp in TIMEPOINTS:
        ids = [g for g in meta.index[meta.timepoint == tp] if g in S.index]
        sub = S.loc[ids]
        lab = meta.loc[ids, "label"].values

        for cell in ["Neutrophil", "T_cell", "NLR_score"]:
            a = sub.loc[lab == 1, cell].dropna()
            b = sub.loc[lab == 0, cell].dropna()
            if len(a) < 3 or len(b) < 3:
                continue
            u, p, r = C.rank_biserial(a, b)
            rows.append({"timepoint": tp, "cell_type": cell,
                         "n_unfavourable": len(a), "n_cured": len(b),
                         "median_unfavourable": float(a.median()),
                         "median_cured": float(b.median()),
                         "rank_biserial_r": float(r), "p_value": float(p)})

        # Matched-timepoint transfer, plus the week-24 signature as an
        # exploratory cross-timepoint check: the discovery arm with a strong
        # signal has no counterpart in this cohort, which stops at week 4.
        for arm, kind in [(ARM_MAP[tp], "matched timepoint"),
                          ("week_24", "cross-timepoint")]:
            if arm == ARM_MAP[tp] and kind == "cross-timepoint":
                continue
            weights = discovery_signature(arm)
            score, n_shared = transfer_score(expr[ids], weights)
            if score is None:
                continue
            auc = roc_auc_score(lab, score)
            u, p = mannwhitneyu(score[lab == 1], score[lab == 0],
                                alternative="two-sided")
            lo, hi = boot_auc_ci(lab, score)
            auc_rows.append({"timepoint": tp, "discovery_arm": C.ARM_LABEL[arm],
                             "comparison": kind,
                             "genes_transferred": int(n_shared),
                             "n": int(len(lab)), "n_relapse": int(lab.sum()),
                             "roc_auc": float(auc), "ci_low": lo, "ci_high": hi,
                             "p_value": float(p)})

    stats = pd.DataFrame(rows)
    aucs = pd.DataFrame(auc_rows)
    stats.to_csv(f"{C.TAB}/external_celltype_stats.csv", index=False)
    aucs.to_csv(f"{C.TAB}/external_transfer_auc.csv", index=False)
    print("\ncell-composition replication:")
    print(stats.to_string(index=False))
    print("\nsignature transfer from discovery:")
    print(aucs.to_string(index=False))

    # ---- Figure ----
    fig, axes = plt.subplots(2, len(TIMEPOINTS), figsize=(4.2 * len(TIMEPOINTS), 7.2))
    for j, tp in enumerate(TIMEPOINTS):
        ids = [g for g in meta.index[meta.timepoint == tp] if g in S.index]
        sub = S.loc[ids]
        lab = meta.loc[ids, "label"].values
        for i, cell in enumerate(["Neutrophil", "T_cell"]):
            ax = axes[i, j]
            groups = [sub.loc[lab == 0, cell].dropna().values,
                      sub.loc[lab == 1, cell].dropna().values]
            parts = ax.violinplot(groups, positions=[0, 1], widths=0.75,
                                  showextrema=False)
            for k, pc in enumerate(parts["bodies"]):
                pc.set_facecolor(["#4C72B0", "#C44E52"][k])
                pc.set_alpha(0.45)
            for k, g in enumerate(groups):
                ax.scatter(np.random.default_rng(C.SEED + k).normal(k, 0.05, len(g)),
                           g, s=18, color=["#2F4B7C", "#8C2F33"][k], alpha=0.85,
                           zorder=3, linewidths=0)
                ax.hlines(np.median(g), k - 0.28, k + 0.28, color="black", lw=2,
                          zorder=4)
            row = stats[(stats.timepoint == tp) & (stats.cell_type == cell)]
            if len(row):
                row = row.iloc[0]
                ax.set_title(f"{tp}\np = {row.p_value:.3f}, r = {row.rank_biserial_r:+.2f}",
                             fontsize=10)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([f"Cured\n(n={len(groups[0])})",
                                f"Relapse\n(n={len(groups[1])})"], fontsize=9)
            if j == 0:
                ax.set_ylabel(f"{'Neutrophil' if i == 0 else 'T cell'} score (z)",
                              fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_external_replication.png", dpi=300)
    plt.close(fig)

    with open(f"{C.TAB}/external_summary.json", "w") as fh:
        json.dump({"cohort": "GSE67589",
                   "patients": int(meta["patient"].nunique()),
                   "arrays": int(len(meta)),
                   "celltype": stats.to_dict("records"),
                   "transfer": aucs.to_dict("records")}, fh, indent=2)
    print("\nwrote external_celltype_stats.csv, external_transfer_auc.csv, "
          "Figure_external_replication.png")


if __name__ == "__main__":
    main()
