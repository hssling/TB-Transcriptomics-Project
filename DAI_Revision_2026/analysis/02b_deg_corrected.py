"""RECHECK FIX: recompute DEG with TRUE log2 fold-changes from the single-log
matrix (GSE89403_log2ExpGeneNames), since the modelling matrix is double-logged.
Mann-Whitney p-values are rank-based and unchanged; only the fold-change axis is
corrected. Maps sample_code (e.g. S100_DX) -> baseline DX sample_ids.
"""
import re, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")
import common

T = f"{common.ROOT}/DAI_Revision_2026/tables"
Fg = f"{common.ROOT}/DAI_Revision_2026/figures"

X, y, meta = common.load_baseline()
# sample_code per baseline sample
meta["sample_code"] = meta["characteristics"].apply(
    lambda s: re.search(r"sample_code:\s*([^|]+)", s).group(1).strip()
    if isinstance(s, str) and "sample_code:" in s else None)
code2label = dict(zip(meta["sample_code"], y.values))

log2 = pd.read_csv(f"{common.ROOT}/outputs/expression/"
                   "GSE89403_log2ExpGeneNames_AllSamples.csv.gz", index_col=0)
symbols = log2["symbol"]
expr = log2.drop(columns=["symbol"]).apply(pd.to_numeric, errors="coerce")
print("log2 matrix:", expr.shape, "range", round(float(np.nanmin(expr.values)), 2),
      round(float(np.nanmax(expr.values)), 2))

# keep only DX baseline sample columns present in our labelled set
cols = [c for c in expr.columns if c in code2label]
print("matched baseline DX columns:", len(cols),
      "| failures:", sum(code2label[c] == 1 for c in cols))
lab = np.array([code2label[c] for c in cols])
E = expr[cols]

fail_cols = [c for c in cols if code2label[c] == 1]
cure_cols = [c for c in cols if code2label[c] == 0]
rows = []
for g in E.index:
    a = E.loc[g, fail_cols].dropna().values
    b = E.loc[g, cure_cols].dropna().values
    if len(a) < 3 or len(b) < 5:
        continue
    try:
        u, p = mannwhitneyu(a, b, alternative="two-sided")
    except ValueError:
        continue
    log2fc = float(np.mean(a) - np.mean(b))   # TRUE log2 fold-change
    rows.append((g, symbols.get(g, g), np.mean(a), np.mean(b), log2fc, p))
deg = pd.DataFrame(rows, columns=["ensembl", "gene_symbol", "mean_failure_log2",
                                  "mean_cure_log2", "log2FC", "p_value"])
deg["fdr"] = multipletests(deg["p_value"], method="fdr_bh")[1]
deg = deg.sort_values("p_value").reset_index(drop=True)
deg.to_csv(f"{T}/wpB_DEG_corrected.csv", index=False)
print("nominal p<0.05:", int((deg.p_value < 0.05).sum()),
      "| FDR<0.05:", int((deg.fdr < 0.05).sum()))
print("max |log2FC| among p<0.05:",
      round(float(deg.loc[deg.p_value < 0.05, "log2FC"].abs().max()), 2))
print("\nTop 12 DEGs (true log2FC):")
print(deg.head(12)[["gene_symbol", "log2FC", "p_value", "fdr"]].to_string(index=False))

# Volcano with corrected axis
d = deg.dropna(subset=["log2FC", "p_value"]).copy()
d["nlp"] = -np.log10(d["p_value"].clip(lower=1e-300))
sig = (d.p_value < 0.05) & (d.log2FC.abs() > 0.5)
plt.figure(figsize=(9, 7))
plt.scatter(d.loc[~sig, "log2FC"], d.loc[~sig, "nlp"], s=8, c="#bbb", alpha=0.5, label="NS")
plt.scatter(d.loc[sig & (d.log2FC > 0), "log2FC"], d.loc[sig & (d.log2FC > 0), "nlp"],
            s=16, c="#cc3333", alpha=0.8, label="Up in failure")
plt.scatter(d.loc[sig & (d.log2FC < 0), "log2FC"], d.loc[sig & (d.log2FC < 0), "nlp"],
            s=16, c="#3366cc", alpha=0.8, label="Down in failure")
for _, r in d.nsmallest(12, "p_value").iterrows():
    plt.annotate(r["gene_symbol"], (r["log2FC"], r["nlp"]), fontsize=9, ha="center")
plt.axhline(-np.log10(0.05), color="k", ls="--", lw=0.8)
plt.axvline(0.5, color="k", ls=":", lw=0.6); plt.axvline(-0.5, color="k", ls=":", lw=0.6)
plt.xlabel("log2 fold-change (Failure - Cure), true log2 scale", fontsize=13)
plt.ylabel("-log10(p)", fontsize=13)
plt.title("Baseline DEG (corrected log2FC): TB failure vs cure", fontsize=13)
plt.legend(fontsize=10); plt.tight_layout()
plt.savefig(f"{Fg}/Figure_volcano.png", dpi=300)  # overwrite with corrected
plt.close()
print("\nOverwrote Figure_volcano.png with corrected log2FC; saved wpB_DEG_corrected.csv")
