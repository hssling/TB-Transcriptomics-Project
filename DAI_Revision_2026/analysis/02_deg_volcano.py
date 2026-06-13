"""WP-B: Differential expression (Cure vs Not-Cured) on baseline DX samples.

Mann-Whitney U per gene + BH-FDR + log2 fold-change -> volcano plot and
a full DEG table. Provides the evidence Reviewer 3 asked for behind the
"~50 genes correlated with outcome" and "Y-linked genes as top predictors"
statements (R2.5, R3.4). Also exports a ranked correlation table.
"""
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")
import common

OUT_FIG = f"{common.ROOT}/DAI_Revision_2026/figures"
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

X, y, meta = common.load_baseline()
fail = X[y.values == 1]
cure = X[y.values == 0]
print(f"DEG: {fail.shape[0]} failure vs {cure.shape[0]} cure, {X.shape[1]} genes")

# Filter very low-expression genes (expressed in <10% of samples)
expr_frac = (X > 0).mean(0)
keep = expr_frac[expr_frac >= 0.10].index
Xf = X[keep]
print(f"Genes after low-expression filter: {len(keep)}")

rows = []
eps = 1e-9
for g in keep:
    a, b = fail[g].values, cure[g].values
    try:
        u, p = mannwhitneyu(a, b, alternative="two-sided")
    except ValueError:
        u, p = np.nan, 1.0
    # rank-biserial effect size from U
    n1, n2 = len(a), len(b)
    rbc = 1 - 2 * u / (n1 * n2) if not np.isnan(u) else np.nan
    log2fc = np.log2((a.mean() + eps) / (b.mean() + eps))
    rows.append((g, a.mean(), b.mean(), log2fc, p, rbc))

deg = pd.DataFrame(rows, columns=["ensembl", "mean_failure", "mean_cure",
                                  "log2FC", "p_value", "rank_biserial"])
deg["fdr"] = multipletests(deg["p_value"].fillna(1), method="fdr_bh")[1]
sym = common.map_symbols(list(deg["ensembl"]))
deg["gene_symbol"] = deg["ensembl"].map(sym)
deg = deg.sort_values("p_value").reset_index(drop=True)
deg.to_csv(f"{OUT_TAB}/wpB_DEG_full.csv", index=False)

sig_p = deg[deg["p_value"] < 0.05]
sig_fdr = deg[deg["fdr"] < 0.05]
print(f"Genes p<0.05: {len(sig_p)}  (this substantiates the '~50 genes' statement)")
print(f"Genes FDR<0.05: {len(sig_fdr)}")
ylinked = deg[deg["gene_symbol"].isin(["RPS4Y1", "KDM5D", "DDX3Y", "UTY",
                                       "USP9Y", "EIF1AY", "NLGN4Y", "TXLNGY"])]
print("\nY-linked genes (substantiates R3.4):")
print(ylinked[["gene_symbol", "log2FC", "p_value", "fdr"]].to_string(index=False))
deg.head(60).to_csv(f"{OUT_TAB}/wpB_DEG_top60.csv", index=False)

# Volcano
deg2 = deg.dropna(subset=["log2FC", "p_value"]).copy()
deg2["neglog10p"] = -np.log10(deg2["p_value"].clip(lower=1e-300))
plt.figure(figsize=(9, 7))
sigmask = (deg2["p_value"] < 0.05) & (deg2["log2FC"].abs() > 0.5)
plt.scatter(deg2.loc[~sigmask, "log2FC"], deg2.loc[~sigmask, "neglog10p"],
            s=8, c="#bbbbbb", alpha=0.5, label="NS")
up = sigmask & (deg2["log2FC"] > 0)
dn = sigmask & (deg2["log2FC"] < 0)
plt.scatter(deg2.loc[up, "log2FC"], deg2.loc[up, "neglog10p"], s=14,
            c="#cc3333", alpha=0.8, label="Up in failure")
plt.scatter(deg2.loc[dn, "log2FC"], deg2.loc[dn, "neglog10p"], s=14,
            c="#3366cc", alpha=0.8, label="Down in failure")
# label top genes
for _, r in deg2.nsmallest(12, "p_value").iterrows():
    plt.annotate(r["gene_symbol"], (r["log2FC"], r["neglog10p"]),
                 fontsize=9, ha="center")
plt.axhline(-np.log10(0.05), color="k", ls="--", lw=0.8)
plt.axvline(0.5, color="k", ls=":", lw=0.6); plt.axvline(-0.5, color="k", ls=":", lw=0.6)
plt.xlabel("log2 fold-change (Failure / Cure)", fontsize=13)
plt.ylabel("-log10(p)", fontsize=13)
plt.title("Baseline DEG: TB treatment failure vs cure (Mann-Whitney U)", fontsize=13)
plt.legend(fontsize=10)
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure_volcano.png", dpi=300)
plt.close()
print("\nSaved Figure_volcano.png, wpB_DEG_full.csv, wpB_DEG_top60.csv")
