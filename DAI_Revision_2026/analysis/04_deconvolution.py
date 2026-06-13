"""WP-D: Marker-based immune-cell deconvolution on baseline samples.

Transparent, reproducible digital cytometry by canonical marker-gene-set
Z-score enrichment (we describe it honestly as such, not proprietary
CIBERSORT). Produces:
 - Violin plots (Failure vs Cure) for Neutrophil & T-cell scores with
   Mann-Whitney U p-values AND rank-biserial effect sizes (R2.12)
 - Significance annotations (R3 minor)
 - Quantified concordance between the deconvolution Neutrophil score and the
   model's predicted failure probability / DEG-derived neutrophil signature
   (R2.7 CIBERSORT<->ML alignment)
"""
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, spearmanr
warnings.filterwarnings("ignore")
import common

OUT_FIG = f"{common.ROOT}/DAI_Revision_2026/figures"
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

# Canonical immune marker gene sets (HGNC symbols)
MARKERS = {
    "Neutrophil": ["FCGR3B", "CSF3R", "CXCR2", "CXCR1", "S100A8", "S100A9",
                   "S100A12", "MPO", "ELANE", "FUT4", "CEACAM3", "FFAR2",
                   "PROK2", "MMP8", "MMP9", "DEFA1", "DEFA3", "DEFA4",
                   "LCN2", "CAMP", "LTF", "BPI"],
    "T_cell": ["CD3D", "CD3E", "CD3G", "CD2", "CD28", "IL7R", "CD8A", "CD8B",
               "LCK", "TRAC", "TRBC2", "CCR7", "CD27", "CD5", "ITK", "TCF7"],
    "Monocyte": ["CD14", "LYZ", "CSF1R", "FCN1", "VCAN", "S100A12", "CD68",
                 "CSF3R", "ITGAM"],
    "B_cell": ["CD19", "MS4A1", "CD79A", "CD79B", "IGHM", "BANK1", "TCL1A"],
    "NK_cell": ["NCAM1", "KLRD1", "NKG7", "GNLY", "KLRF1", "NCR1", "PRF1"],
}

X, y, meta = common.load_baseline()
yv = y.values
# map our Ensembl columns to symbols
sym = common.map_symbols(list(X.columns))
sym2ens = {}
for e, s in sym.items():
    sym2ens.setdefault(s, []).append(e)

# Z-score genes across samples
Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)

scores = {}
used = {}
for cell, genes in MARKERS.items():
    cols = []
    for g in genes:
        cols.extend(sym2ens.get(g, []))
    cols = [c for c in cols if c in Xz.columns]
    used[cell] = len(cols)
    scores[cell] = Xz[cols].mean(1) if cols else pd.Series(np.nan, index=Xz.index)
S = pd.DataFrame(scores)
S["NLR_score"] = S["Neutrophil"] - S["T_cell"]  # neutrophil-lymphocyte axis
S["y"] = yv
S.to_csv(f"{OUT_TAB}/wpD_celltype_scores.csv")
print("Markers used per cell type:", used)


def rank_biserial(a, b):
    u, p = mannwhitneyu(a, b, alternative="two-sided")
    r = 1 - 2 * u / (len(a) * len(b))  # failure relative to cure
    return u, p, r


stats = {}
for cell in ["Neutrophil", "T_cell", "Monocyte", "B_cell", "NK_cell", "NLR_score"]:
    a = S.loc[S.y == 1, cell].dropna()
    b = S.loc[S.y == 0, cell].dropna()
    u, p, r = rank_biserial(a.values, b.values)
    stats[cell] = {"median_failure": float(a.median()),
                   "median_cure": float(b.median()),
                   "mannwhitney_p": float(p), "rank_biserial_r": float(r)}
    print(f"{cell:11s} failure-med={a.median():+.2f} cure-med={b.median():+.2f} "
          f"p={p:.2e} rank-biserial r={r:+.2f}")
pd.DataFrame(stats).T.to_csv(f"{OUT_TAB}/wpD_violin_stats.csv")

# ---- Violin figure ----
cells = ["Neutrophil", "T_cell", "NLR_score"]
fig, axes = plt.subplots(1, 3, figsize=(13, 5))
for ax, cell in zip(axes, cells):
    data = [S.loc[S.y == 0, cell].dropna().values,
            S.loc[S.y == 1, cell].dropna().values]
    parts = ax.violinplot(data, showmedians=True, showextrema=True)
    for pc, c in zip(parts["bodies"], ["#4477aa", "#cc3333"]):
        pc.set_facecolor(c); pc.set_alpha(0.6)
    # jitter points
    for i, d in enumerate(data):
        ax.scatter(np.random.normal(i + 1, 0.05, len(d)), d, s=18,
                   c="k", alpha=0.5, zorder=3)
    ax.set_xticks([1, 2]); ax.set_xticklabels(["Cure (0)", "Failure (1)"], fontsize=12)
    st = stats[cell]
    ax.set_title(f"{cell}\nMWU p={st['mannwhitney_p']:.1e}, "
                 f"r={st['rank_biserial_r']:+.2f}", fontsize=12)
    ax.set_ylabel("Marker-set Z-score", fontsize=12)
    # significance bracket
    ymax = max(np.max(data[0]), np.max(data[1]))
    ax.plot([1, 2], [ymax + 0.3, ymax + 0.3], "k-", lw=1)
    star = "***" if st["mannwhitney_p"] < 1e-3 else ("**" if st["mannwhitney_p"] < 1e-2 else ("*" if st["mannwhitney_p"] < 0.05 else "ns"))
    ax.text(1.5, ymax + 0.4, star, ha="center", fontsize=14)
plt.suptitle("Baseline immune-cell deconvolution: Failure vs Cure", fontsize=14)
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure2_deconvolution_violins.png", dpi=300)
plt.close()

# ---- Concordance: deconvolution Neutrophil score vs ML failure probability ----
try:
    oof = pd.read_csv(f"{OUT_TAB}/wpA_oof_predictions.csv").set_index("sample_id")
    best_col = [c for c in oof.columns if c.startswith("oof_")]
    # pick the column matching best model from wpA json
    import json
    bm = json.load(open(f"{OUT_TAB}/wpA_metric_suite.json"))["best_model"]
    pcol = f"oof_{bm}"
    common_idx = S.index.intersection(oof.index)
    rho, pv = spearmanr(S.loc[common_idx, "Neutrophil"], oof.loc[common_idx, pcol])
    rho_t, pv_t = spearmanr(S.loc[common_idx, "T_cell"], oof.loc[common_idx, pcol])
    print(f"\nConcordance (R2.7): Neutrophil score vs ML failure prob: "
          f"Spearman rho={rho:.2f}, p={pv:.2e}")
    print(f"                    T-cell score vs ML failure prob:     "
          f"Spearman rho={rho_t:.2f}, p={pv_t:.2e}")
    conc = {"neutrophil_vs_ML_prob": {"spearman_rho": float(rho), "p": float(pv)},
            "tcell_vs_ML_prob": {"spearman_rho": float(rho_t), "p": float(pv_t)},
            "best_model": bm, "n": int(len(common_idx))}
    json.dump(conc, open(f"{OUT_TAB}/wpD_concordance.json", "w"), indent=2)
except Exception as e:
    print("Concordance step skipped (run WP-A first):", e)

print("\nSaved Figure2_deconvolution_violins.png + wpD tables")
