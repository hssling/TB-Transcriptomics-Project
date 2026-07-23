"""Performance figures and the cross-state contrast.

The contrast is the point of separating the arms: it shows where in the
treatment course whole blood carries outcome information, which parts of the
signal persist across states, and which appear only once therapy has perturbed
the system.
"""
import json
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (precision_recall_curve, roc_curve)

warnings.filterwarnings("ignore")

MODEL_NICE = {"logistic_regression": "Logistic regression",
              "random_forest": "Random forest",
              "gradient_boosting": "Gradient boosting"}
MODEL_COLOR = {"logistic_regression": "#4C72B0",
               "random_forest": "#C44E52",
               "gradient_boosting": "#55A868"}
INKC = "#2B2B2B"


def performance_figure(metrics, oof):
    fig, axes = plt.subplots(3, len(C.ARMS), figsize=(4.3 * len(C.ARMS), 11.4))
    for j, arm in enumerate(C.ARMS):
        m = metrics[arm]
        sub = oof[oof.arm == arm]
        y = sub["label"].values
        p = sub["pred_prob"].values

        ax = axes[0, j]
        for name, res in m["models"].items():
            # Curves are drawn for the arm's selected model; the others are
            # summarised by their AUC in the legend.
            if name == m["best_model"]:
                fpr, tpr, _ = roc_curve(y, p)
                ax.plot(fpr, tpr, color=MODEL_COLOR[name], lw=2.1,
                        label=f"{MODEL_NICE[name]} {res['roc_auc']:.2f}")
            else:
                ax.plot([], [], color=MODEL_COLOR[name], lw=1.4, ls="--",
                        label=f"{MODEL_NICE[name]} {res['roc_auc']:.2f}")
        ax.plot([0, 1], [0, 1], color="#999999", lw=0.9, ls=":")
        ax.set_xlabel("1 − specificity", fontsize=9)
        if j == 0:
            ax.set_ylabel("Sensitivity", fontsize=10)
        ax.set_title(f"{C.ARM_LABEL[arm]}\nn = {m['n']}, {m['n_events']} unfavourable",
                     fontsize=11, fontweight="bold")
        ax.legend(fontsize=7.6, frameon=False, loc="lower right")

        ax = axes[1, j]
        prec, rec, _ = precision_recall_curve(y, p)
        best = m["models"][m["best_model"]]
        ax.plot(rec, prec, color=MODEL_COLOR[m["best_model"]], lw=2.1)
        ax.axhline(m["n_events"] / m["n"], color="#999999", lw=0.9, ls=":")
        ax.set_xlabel("Recall", fontsize=9)
        if j == 0:
            ax.set_ylabel("Precision", fontsize=10)
        ax.set_title(f"PR-AUC {best['pr_auc']:.2f} "
                     f"(prevalence {m['n_events'] / m['n']:.2f})", fontsize=9.5)

        ax = axes[2, j]
        cm = best["confusion"]
        mat = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        ax.imshow(mat, cmap="Blues", vmin=0, vmax=mat.max())
        for a in range(2):
            for b in range(2):
                ax.text(b, a, mat[a, b], ha="center", va="center", fontsize=15,
                        color="white" if mat[a, b] > mat.max() * 0.55 else INKC)
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        ax.set_xticklabels(["Predicted\ncured", "Predicted\nunfavourable"], fontsize=8.5)
        ax.set_yticklabels(["Cured", "Unfavourable"], fontsize=8.5)
        pc = {r["class"]: r for r in best["per_class"]}
        ax.set_title("Unfavourable: sens {:.2f}, spec {:.2f}\n"
                     "Cured: sens {:.2f}, spec {:.2f}".format(
                         pc["Unfavourable"]["sensitivity"],
                         pc["Unfavourable"]["specificity"],
                         pc["Cured"]["sensitivity"],
                         pc["Cured"]["specificity"]), fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_performance_arms.png", dpi=300)
    plt.close(fig)


def comparative_figure(metrics, decon, shap_rank, partition):
    fig = plt.figure(figsize=(13.6, 9.6))
    gs = fig.add_gridspec(2, 2, hspace=0.36, wspace=0.28)

    # (A) discrimination across states
    ax = fig.add_subplot(gs[0, 0])
    arms = [a for a in C.ARMS + ["combined"] if a in metrics]
    ys = np.arange(len(arms))[::-1]
    for k, arm in enumerate(arms):
        m = metrics[arm]
        best = m["models"][m["best_model"]]
        lo, hi = best["roc_auc_ci"]
        col = "#7A7A7A" if arm == "combined" else "#C44E52"
        ax.plot([lo, hi], [ys[k], ys[k]], color=col, lw=2.4, solid_capstyle="round")
        ax.plot(best["roc_auc"], ys[k], "o", color=col, ms=9)
        ax.text(hi + 0.015, ys[k],
                f"{best['roc_auc']:.2f} ({lo:.2f}–{hi:.2f})  p = {m['permutation']['permutation_p']:.3f}",
                va="center", fontsize=8.6)
    ax.axvline(0.5, color="#999999", lw=1.0, ls=":")
    ax.set_yticks(ys)
    ax.set_yticklabels([C.ARM_LABEL[a] for a in arms], fontsize=10)
    ax.set_xlim(0.25, 1.32)
    ax.set_xticks([0.3, 0.5, 0.7, 0.9, 1.0])
    ax.set_xlabel("ROC-AUC with 95% confidence interval", fontsize=9.5)
    ax.set_title("A  Discrimination by biological state", fontsize=11,
                 fontweight="bold", loc="left")

    # (B) cell-composition effect sizes across states
    ax = fig.add_subplot(gs[0, 1])
    cells = ["Neutrophil", "T cell", "Neutrophil - T cell"]
    width = 0.26
    xs = np.arange(len(C.ARMS))
    for i, cell in enumerate(cells):
        vals, sig = [], []
        for arm in C.ARMS:
            r = decon[(decon.arm == arm) & (decon.cell_type == cell)]
            vals.append(float(r["rank_biserial_r"].iloc[0]) if len(r) else np.nan)
            sig.append(float(r["p_value"].iloc[0]) if len(r) else 1.0)
        bars = ax.bar(xs + (i - 1) * width, vals, width,
                      color=["#C44E52", "#4C72B0", "#55A868"][i], label=cell)
        for b, p in zip(bars, sig):
            if p < 0.05:
                ax.text(b.get_x() + b.get_width() / 2,
                        b.get_height() + (0.03 if b.get_height() >= 0 else -0.08),
                        "*", ha="center", fontsize=13)
    ax.axhline(0, color=INKC, lw=0.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([C.ARM_LABEL[a] for a in C.ARMS], fontsize=9.5)
    ax.set_ylabel("Rank-biserial r\n(unfavourable vs cured)", fontsize=9.5)
    ax.legend(fontsize=8.5, frameon=False)
    ax.set_title("B  Immune composition by biological state", fontsize=11,
                 fontweight="bold", loc="left")

    # (C) where the transcriptional signal lives
    ax = fig.add_subplot(gs[1, 0])
    order = ["pre_treatment_only", "stable_across_states", "post_treatment_only"]
    nice = {"pre_treatment_only": "Pre-treatment only",
            "stable_across_states": "Stable across states",
            "post_treatment_only": "Post-treatment only"}
    counts = [int((partition["class"] == c).sum()) for c in order]
    bars = ax.barh(np.arange(len(order))[::-1], counts,
                   color=["#C44E52", "#8E7CC3", "#55A868"])
    for b, c in zip(bars, counts):
        ax.text(b.get_width() + max(counts) * 0.015, b.get_y() + b.get_height() / 2,
                str(c), va="center", fontsize=9.5)
    ax.set_yticks(np.arange(len(order))[::-1])
    ax.set_yticklabels([nice[c] for c in order], fontsize=9.5)
    ax.set_xlabel("Genes separating outcome groups (p < 0.01)", fontsize=9.5)
    ax.set_xlim(0, max(counts) * 1.16)
    ax.set_title("C  Stability of the transcriptional signal", fontsize=11,
                 fontweight="bold", loc="left")

    # (D) overlap of the model's feature panels
    ax = fig.add_subplot(gs[1, 1])
    panels = {arm: set(shap_rank[(shap_rank.arm == arm) &
                                 (shap_rank["rank"] <= 25)]["ensembl"])
              for arm in C.ARMS}
    n = len(C.ARMS)
    mat = np.zeros((n, n))
    for a in range(n):
        for b in range(n):
            pa, pb = panels[C.ARMS[a]], panels[C.ARMS[b]]
            mat[a, b] = len(pa & pb) / max(1, len(pa | pb))
    im = ax.imshow(mat, cmap="PuBu", vmin=0, vmax=1)
    for a in range(n):
        for b in range(n):
            ax.text(b, a, f"{mat[a, b]:.2f}", ha="center", va="center",
                    fontsize=9.5,
                    color="white" if mat[a, b] > 0.55 else INKC)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([C.ARM_LABEL[a] for a in C.ARMS], fontsize=9, rotation=20,
                       ha="right")
    ax.set_yticklabels([C.ARM_LABEL[a] for a in C.ARMS], fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03,
                 label="Jaccard overlap")
    ax.set_title("D  Shared features between states (top 25 by SHAP)",
                 fontsize=11, fontweight="bold", loc="left")

    fig.savefig(f"{C.FIG}/Figure_comparative.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    metrics = json.load(open(f"{C.TAB}/arm_metrics.json"))
    oof = pd.read_csv(f"{C.TAB}/arm_oof_predictions.csv")
    decon = pd.read_csv(f"{C.TAB}/deconvolution_stats.csv")
    shap_rank = pd.read_csv(f"{C.TAB}/shap_feature_ranking.csv")
    partition = pd.read_csv(f"{C.TAB}/deg_state_partition.csv")

    performance_figure(metrics, oof)
    comparative_figure(metrics, decon, shap_rank, partition)

    rows = []
    for arm in [a for a in C.ARMS + ["combined"] if a in metrics]:
        m = metrics[arm]
        best = m["models"][m["best_model"]]
        pc = {r["class"]: r for r in best["per_class"]}
        rows.append({
            "arm": C.ARM_LABEL[arm],
            "n": m["n"], "unfavourable": m["n_events"],
            "model": MODEL_NICE[m["best_model"]],
            "roc_auc": round(best["roc_auc"], 3),
            "ci_low": round(best["roc_auc_ci"][0], 3),
            "ci_high": round(best["roc_auc_ci"][1], 3),
            "pr_auc": round(best["pr_auc"], 3),
            "sens_unfavourable": round(pc["Unfavourable"]["sensitivity"], 3),
            "spec_unfavourable": round(pc["Unfavourable"]["specificity"], 3),
            "ppv_unfavourable": round(pc["Unfavourable"]["ppv"], 3),
            "npv_unfavourable": round(pc["Unfavourable"]["npv"], 3),
            "sens_cured": round(pc["Cured"]["sensitivity"], 3),
            "spec_cured": round(pc["Cured"]["specificity"], 3),
            "mcc": round(best["mcc"], 3),
            "brier": round(best["brier"], 3),
            "permutation_p": round(m["permutation"]["permutation_p"], 4),
            "loo_auc": round(m.get("loo_auc", float("nan")), 3)
            if m.get("loo_auc") is not None else "",
        })
    tab = pd.DataFrame(rows)
    tab.to_csv(f"{C.TAB}/arm_performance_table.csv", index=False)
    print(tab.to_string(index=False))
    print("\nwrote Figure_performance_arms.png, Figure_comparative.png, "
          "arm_performance_table.csv")


if __name__ == "__main__":
    main()
