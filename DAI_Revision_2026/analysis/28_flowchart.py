"""Study flow diagram: cohort assembly, the three arms, and the verification
chain applied to the machine-learning output.
"""
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

warnings.filterwarnings("ignore")

INK = "#2B2B2B"
FILL_DATA = "#E8EEF6"
FILL_ARM = "#F3E8E4"
FILL_METHOD = "#EAF1E7"
FILL_EXT = "#F5EFE0"


def box(ax, x, y, w, h, text, fill, fontsize=9, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.1, edgecolor=INK, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=INK, fontweight=weight, linespacing=1.45)


def arrow(ax, xy_from, xy_to, style="-|>"):
    ax.add_patch(FancyArrowPatch(xy_from, xy_to, arrowstyle=style,
                                 mutation_scale=13, linewidth=1.0,
                                 color=INK, shrinkA=1, shrinkB=1))


def main():
    fig, ax = plt.subplots(figsize=(13.2, 10.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    spine = 0.40   # centre of the cohort-assembly column

    box(ax, spine - 0.23, 0.925, 0.46, 0.062,
        "GSE89403 — whole-blood RNA sequencing\n"
        "pulmonary tuberculosis treatment-response cohort",
        FILL_DATA, 10.5, "bold")

    box(ax, spine - 0.26, 0.812, 0.52, 0.072,
        "914 deposited libraries\n"
        "lane replicates merged → 453 biological samples",
        FILL_DATA, 9)
    arrow(ax, (spine, 0.925), (spine, 0.884))

    box(ax, 0.705, 0.812, 0.27, 0.072,
        "Excluded: non-tuberculosis\ncontrols, unevaluable or\nunrecorded outcome",
        "#FFFFFF", 8.5)
    arrow(ax, (spine + 0.26, 0.848), (0.705, 0.848))

    box(ax, spine - 0.26, 0.700, 0.52, 0.072,
        "367 libraries from 98 subjects with a recorded outcome\n"
        "16,145 genes retained · counts per million · log$_2$(x+1)",
        FILL_DATA, 9.5)
    arrow(ax, (spine, 0.812), (spine, 0.772))

    arm_defs = [
        (0.035, "Pre-treatment\n(diagnosis)", "n = 90\n7 unfavourable",
         "Intrinsic patient biology\nbefore therapy"),
        (0.275, "Day 7", "n = 91\n6 unfavourable",
         "Early treatment-induced\nimmune shift"),
        (0.515, "Week 4", "n = 92\n8 unfavourable",
         "End of intensive phase"),
        (0.755, "Week 24", "n = 94\n7 unfavourable",
         "End of therapy\nresolved vs unresolved"),
    ]
    # Distribute through a horizontal bus so the fan-out reads cleanly.
    bus_y = 0.652
    arm_top, arm_bot = 0.610, 0.470
    centres = [x + 0.105 for x, *_ in arm_defs]
    arrow(ax, (spine, 0.700), (spine, bus_y), style="-")
    ax.plot([min(centres), max(centres)], [bus_y, bus_y], color=INK, lw=1.0)
    for x, title, n, meaning in arm_defs:
        cx = x + 0.105
        arrow(ax, (cx, bus_y), (cx, arm_top))
        box(ax, x, arm_bot, 0.21, arm_top - arm_bot, "", FILL_ARM)
        ax.text(cx, 0.592, title, ha="center", va="top", fontsize=10,
                fontweight="bold", color=INK, linespacing=1.4)
        ax.text(cx, 0.534, n, ha="center", va="top", fontsize=9.5, color=INK,
                linespacing=1.4)
        ax.text(cx, 0.503, meaning, ha="center", va="top", fontsize=8,
                color="#5A5A5A", style="italic", linespacing=1.35)

    box(ax, 0.055, 0.372, 0.89, 0.055,
        "Identical modelling protocol in every arm — penalised logistic regression, random forest, gradient boosting\n"
        "feature pre-selection inside each training fold · repeated stratified five-fold cross-validation · pooled out-of-fold probabilities",
        FILL_METHOD, 9)
    for cx in centres:
        arrow(ax, (cx, arm_bot), (cx, 0.427))

    box(ax, 0.055, 0.272, 0.89, 0.058,
        "Discrimination reported per class — sensitivity, specificity, predictive values, F1\n"
        "with ROC-AUC, precision–recall AUC, Matthews correlation, calibration and a label-permutation null",
        FILL_METHOD, 9)
    arrow(ax, (0.50, 0.372), (0.50, 0.330))

    box(ax, 0.315, 0.176, 0.37, 0.056,
        "SHAP attribution on the gradient-boosted model\n"
        "ranked feature panel per arm",
        FILL_METHOD, 9, "bold")
    arrow(ax, (0.50, 0.272), (0.50, 0.232))

    ver = [
        (0.020, "Immune deconvolution\nmarker-panel enrichment;\ncorrelation with predicted risk"),
        (0.268, "Differential expression\neffect size and\nfalse-discovery control"),
        (0.516, "Conditional-dependency network\ngraphical lasso on the\nSHAP panel"),
        (0.764, "Independent cohort\nGSE67589 — cure vs relapse\nseparate patients and platform"),
    ]
    ver_bus = 0.148
    ver_centres = [x + 0.108 for x, _ in ver]
    arrow(ax, (0.50, 0.176), (0.50, ver_bus), style="-")
    ax.plot([min(ver_centres), max(ver_centres)], [ver_bus, ver_bus],
            color=INK, lw=1.0)
    for x, text in ver:
        cx = x + 0.108
        arrow(ax, (cx, ver_bus), (cx, 0.126))
        box(ax, x, 0.040, 0.216, 0.086, text,
            FILL_EXT if "Independent" in text else FILL_METHOD, 8.5)

    ax.text(0.5, 0.006,
            "Verification of the model-derived signal against established bioinformatic methods and an independent cohort",
            ha="center", fontsize=9, style="italic", color="#555555")

    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_study_flow.png", dpi=300,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote Figure_study_flow.png")


if __name__ == "__main__":
    main()
