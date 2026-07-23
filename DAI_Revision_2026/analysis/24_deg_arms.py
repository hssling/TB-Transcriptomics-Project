"""Differential expression within each arm, and the contrast between arms.

The per-arm tests establish which transcripts separate outcome groups in a
given biological state. The contrast then partitions the union of those
transcripts into three classes: stable across states, present only before
treatment, and emerging only after treatment has perturbed the system. That
partition is the substantive product of analysing the states separately.
"""
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")

MIN_DETECTED = 0.10
NOMINAL = 0.01


def deg_for_arm(arm):
    X, y, meta = C.load_arm(arm)
    keep = (X > 0).mean(0) >= MIN_DETECTED
    X = X.loc[:, keep]
    a = X[y.values == 1]
    b = X[y.values == 0]
    stat, pvals = mannwhitneyu(a.values, b.values, alternative="two-sided", axis=0)
    lfc = a.mean(0).values - b.mean(0).values          # already log2 scale
    fdr = multipletests(pvals, method="fdr_bh")[1]
    out = pd.DataFrame({
        "arm": arm, "arm_label": C.ARM_LABEL[arm],
        "ensembl": X.columns, "gene_symbol": C.to_symbols(list(X.columns)),
        "log2_fold_change": lfc, "p_value": pvals, "fdr": fdr,
        "mean_unfavourable": a.mean(0).values, "mean_cured": b.mean(0).values,
    })
    return out.sort_values("p_value").reset_index(drop=True)


def main():
    frames = {arm: deg_for_arm(arm) for arm in C.ARMS}
    allde = pd.concat(frames.values(), ignore_index=True)
    allde.to_csv(f"{C.TAB}/deg_all_arms.csv", index=False)

    summary = []
    for arm, d in frames.items():
        summary.append({
            "arm": arm, "arm_label": C.ARM_LABEL[arm],
            "genes_tested": int(len(d)),
            "nominal_p05": int((d.p_value < 0.05).sum()),
            "nominal_p01": int((d.p_value < NOMINAL).sum()),
            "fdr_significant": int((d.fdr < 0.05).sum()),
            "top_gene": d.iloc[0]["gene_symbol"],
            "top_p": float(d.iloc[0]["p_value"]),
            "top_fdr": float(d.iloc[0]["fdr"]),
        })
    summ = pd.DataFrame(summary)
    summ.to_csv(f"{C.TAB}/deg_summary.csv", index=False)
    print(summ.to_string(index=False))

    # ---- Stable / pre-treatment-only / post-treatment-only partition ----
    sets = {arm: set(d.loc[d.p_value < NOMINAL, "ensembl"]) for arm, d in frames.items()}
    pre = sets["DX"]
    post = sets["day_7"] | sets["week_4"] | sets["week_24"]
    post_all = sets["day_7"] & sets["week_4"] & sets["week_24"]

    partition = {
        "stable_across_states": sorted(pre & post),
        "pre_treatment_only": sorted(pre - post),
        "post_treatment_only": sorted(post - pre),
        "post_treatment_consistent": sorted(post_all),
    }
    rows = []
    for cls, genes in partition.items():
        for g in genes:
            rows.append({"class": cls, "ensembl": g,
                         "gene_symbol": C.to_symbols([g])[0]})
    part = pd.DataFrame(rows)
    part.to_csv(f"{C.TAB}/deg_state_partition.csv", index=False)
    print("\nState partition of nominal hits (p < %.2f):" % NOMINAL)
    print(part.groupby("class").size().to_string())

    # ---- Volcano panel ----
    fig, axes = plt.subplots(1, len(C.ARMS), figsize=(4.4 * len(C.ARMS), 4.4),
                             sharey=True)
    for j, arm in enumerate(C.ARMS):
        d = frames[arm]
        ax = axes[j]
        sig = d.p_value < NOMINAL
        ax.scatter(d.loc[~sig, "log2_fold_change"],
                   -np.log10(d.loc[~sig, "p_value"]),
                   s=5, color="#BFC4CC", alpha=0.5, linewidths=0)
        ax.scatter(d.loc[sig, "log2_fold_change"],
                   -np.log10(d.loc[sig, "p_value"]),
                   s=9, color="#C44E52", alpha=0.8, linewidths=0)
        for _, r in d.head(6).iterrows():
            ax.annotate(r.gene_symbol, (r.log2_fold_change, -np.log10(r.p_value)),
                        fontsize=7.5, xytext=(3, 2), textcoords="offset points")
        ax.axhline(-np.log10(NOMINAL), color="black", lw=0.8, ls="--")
        ax.axvline(0, color="black", lw=0.6)
        ax.set_title(C.ARM_LABEL[arm], fontsize=12, fontweight="bold")
        ax.set_xlabel("log$_2$ fold change\n(unfavourable vs cured)", fontsize=9)
        if j == 0:
            ax.set_ylabel("$-$log$_{10}$ p", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_volcano_arms.png", dpi=300)
    plt.close(fig)
    print("\nwrote deg_all_arms.csv, deg_summary.csv, deg_state_partition.csv, "
          "Figure_volcano_arms.png")


if __name__ == "__main__":
    main()
