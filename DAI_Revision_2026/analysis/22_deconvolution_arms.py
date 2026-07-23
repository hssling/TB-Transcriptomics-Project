"""Immune composition behind the model signal, in every arm.

Two questions are answered here. First, does marker-based deconvolution
separate outcome groups within each biological state? Second, does the
model's predicted probability track the same cellular axis the deconvolution
recovers - the check that ties the machine-learning step to an established
bioinformatic method rather than leaving it unverified.

Produces the cell-composition violins and the predicted-probability versus
cell-score correlation panel.
"""
import json
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

CELLS = ["Neutrophil", "T_cell", "Monocyte", "B_cell", "NK_cell", "NLR_score"]
NICE = {"Neutrophil": "Neutrophil", "T_cell": "T cell", "Monocyte": "Monocyte",
        "B_cell": "B cell", "NK_cell": "NK cell", "NLR_score": "Neutrophil - T cell"}


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


def main():
    oof = pd.read_csv(f"{C.TAB}/arm_oof_predictions.csv")
    rows, corr_rows = [], []
    all_scores = []

    for arm in C.ARMS:
        X, y, meta = C.load_arm(arm)
        S, used = C.celltype_scores(X)
        S["label"] = y.values
        S["arm"] = arm
        all_scores.append(S.reset_index().rename(columns={"index": "sample_code"}))

        for cell in CELLS:
            a = S.loc[S.label == 1, cell].dropna()
            b = S.loc[S.label == 0, cell].dropna()
            u, p, r = C.rank_biserial(a, b)
            rows.append({"arm": arm, "arm_label": C.ARM_LABEL[arm],
                         "cell_type": NICE[cell],
                         "median_unfavourable": float(a.median()),
                         "median_cured": float(b.median()),
                         "rank_biserial_r": float(r), "p_value": float(p),
                         "n_marker_genes": used.get(cell, np.nan)})

        sub = oof[oof.arm == arm].set_index("sample_code")
        shared = [s for s in S.index if s in sub.index]
        for cell in ["Neutrophil", "T_cell", "NLR_score"]:
            rho, pv = spearmanr(sub.loc[shared, "pred_prob"], S.loc[shared, cell])
            corr_rows.append({"arm": arm, "arm_label": C.ARM_LABEL[arm],
                              "cell_type": NICE[cell], "n": len(shared),
                              "spearman_rho": float(rho), "p_value": float(pv)})

    stats = pd.DataFrame(rows)
    corr = pd.DataFrame(corr_rows)
    stats.to_csv(f"{C.TAB}/deconvolution_stats.csv", index=False)
    corr.to_csv(f"{C.TAB}/prediction_celltype_correlation.csv", index=False)
    pd.concat(all_scores).to_csv(f"{C.TAB}/celltype_scores.csv", index=False)
    print(stats.to_string(index=False))
    print()
    print(corr.to_string(index=False))

    # ---- Figure: composition by outcome, per arm ----
    show = ["Neutrophil", "T_cell", "NLR_score"]
    fig, axes = plt.subplots(len(show), len(C.ARMS),
                             figsize=(4.0 * len(C.ARMS), 3.3 * len(show)),
                             sharey="row")
    scores = pd.concat(all_scores)
    for j, arm in enumerate(C.ARMS):
        sa = scores[scores.arm == arm]
        for i, cell in enumerate(show):
            ax = axes[i, j]
            groups = [sa.loc[sa.label == 0, cell].dropna().values,
                      sa.loc[sa.label == 1, cell].dropna().values]
            parts = ax.violinplot(groups, positions=[0, 1], widths=0.75,
                                  showextrema=False)
            for k, pc in enumerate(parts["bodies"]):
                pc.set_facecolor(["#4C72B0", "#C44E52"][k])
                pc.set_alpha(0.45)
            for k, g in enumerate(groups):
                ax.scatter(np.random.default_rng(C.SEED + k).normal(k, 0.055, len(g)),
                           g, s=14, color=["#2F4B7C", "#8C2F33"][k], alpha=0.8,
                           zorder=3, linewidths=0)
                ax.hlines(np.median(g), k - 0.28, k + 0.28, color="black", lw=2,
                          zorder=4)
            row = stats[(stats.arm == arm) & (stats.cell_type == NICE[cell])].iloc[0]
            top = max(np.max(groups[0]), np.max(groups[1]))
            ax.text(0.5, top * 1.06 if top > 0 else top * 0.94,
                    f"{stars(row.p_value)}  p={row.p_value:.3f}\nr={row.rank_biserial_r:+.2f}",
                    ha="center", va="bottom", fontsize=9)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([f"Cured\n(n={len(groups[0])})",
                                f"Unfavourable\n(n={len(groups[1])})"], fontsize=9)
            ax.margins(y=0.22)
            if j == 0:
                ax.set_ylabel(f"{NICE[cell]}\nz-score", fontsize=10)
            if i == 0:
                ax.set_title(C.ARM_LABEL[arm], fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_deconvolution_arms.png", dpi=300)
    plt.close(fig)

    # ---- Figure: predicted probability against cell scores ----
    fig, axes = plt.subplots(2, len(C.ARMS), figsize=(4.0 * len(C.ARMS), 7.0))
    for j, arm in enumerate(C.ARMS):
        sa = scores[scores.arm == arm].set_index("sample_code")
        sub = oof[oof.arm == arm].set_index("sample_code")
        shared = [s for s in sa.index if s in sub.index]
        for i, cell in enumerate(["Neutrophil", "T_cell"]):
            ax = axes[i, j]
            xv = sa.loc[shared, cell].values
            yv = sub.loc[shared, "pred_prob"].values
            lab = sub.loc[shared, "label"].values
            for cls, col, nm in [(0, "#4C72B0", "Cured"),
                                 (1, "#C44E52", "Unfavourable")]:
                ax.scatter(xv[lab == cls], yv[lab == cls], s=26, alpha=0.8,
                           color=col, label=nm, linewidths=0)
            b, a = np.polyfit(xv, yv, 1)
            xs = np.linspace(xv.min(), xv.max(), 50)
            ax.plot(xs, a + b * xs, color="black", lw=1.4, ls="--")
            r = corr[(corr.arm == arm) & (corr.cell_type == NICE[cell])].iloc[0]
            ax.set_title(f"{C.ARM_LABEL[arm]}\n"
                         + r"$\rho$" + f" = {r.spearman_rho:+.2f}, p = {r.p_value:.1e}",
                         fontsize=10)
            ax.set_xlabel(f"{NICE[cell]} score (z)", fontsize=9)
            if j == 0:
                ax.set_ylabel("Predicted probability\nof unfavourable outcome",
                              fontsize=9)
            if i == 0 and j == 0:
                ax.legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_prediction_vs_celltype.png", dpi=300)
    plt.close(fig)

    with open(f"{C.TAB}/deconvolution_summary.json", "w") as fh:
        json.dump({"markers_used": used,
                   "correlations": corr.to_dict("records")}, fh, indent=2)
    print("\nwrote deconvolution figures and tables")


if __name__ == "__main__":
    main()
