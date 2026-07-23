"""Within-subject treatment response: how far each patient travels, and where.

The arm analyses compare different patients at one timepoint, so between-subject
variation sits inside every contrast. Paired samples remove it. For each subject
with both a diagnosis and a later sample, the change vector week_t minus
diagnosis describes that individual's response to therapy.

Averaging those vectors across cured subjects defines what a successful
response looks like. Each subject is then scored by how far their own change
aligns with that reference direction, which answers directly whether patients
with an unfavourable outcome fail to make the journey the cured patients make.

The reference is built leave-one-subject-out for cured subjects, so no subject
contributes to the direction used to score them.
"""
import json
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

PAIRS = [("day_7", "Day 7"), ("week_4", "Week 4"), ("week_24", "Week 24")]
TOP_GENES = 2000


def paired_frame(later_arm):
    """Subjects with both a diagnosis and a later sample."""
    Xd, yd, md = C.load_arm("DX")
    Xl, yl, ml = C.load_arm(later_arm)
    sd = md.reset_index().set_index("subject")["sample_code"]
    sl = ml.reset_index().set_index("subject")["sample_code"]
    shared = sorted(set(sd.index) & set(sl.index))
    delta = pd.DataFrame(
        Xl.loc[sl[shared]].values - Xd.loc[sd[shared]].values,
        index=shared, columns=Xd.columns)
    label = ml.reset_index().set_index("subject").loc[shared, "label"]
    return delta, label.astype(int)


def alignment_scores(delta, label):
    """Cosine alignment of each subject's change with the cured-response
    direction, built without that subject when the subject is cured."""
    # Restrict to genes that move most consistently in cured subjects, which
    # is where a treatment response is legible at all.
    cured = delta[label.values == 0]
    t = cured.mean(0) / (cured.std(0) + 1e-9)
    genes = t.abs().nlargest(TOP_GENES).index
    D = delta[genes]

    scores = {}
    for subj in D.index:
        if label.loc[subj] == 0:
            ref = D[(label.values == 0) & (D.index != subj)].mean(0).values
        else:
            ref = D[label.values == 0].mean(0).values
        v = D.loc[subj].values
        denom = np.linalg.norm(v) * np.linalg.norm(ref)
        scores[subj] = float(v @ ref / denom) if denom > 0 else np.nan
    return pd.Series(scores), list(genes)


def delta_classifier(delta, label, n_repeats=20):
    """Same modelling protocol as the arm analyses, applied to the change
    vectors. This is the like-for-like comparison: does the within-subject
    change discriminate as well as the cross-sectional state does?"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_selection import SelectKBest, f_classif
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import Pipeline

    Xv, yv = delta.values, label.values
    acc, cnt = np.zeros(len(yv)), np.zeros(len(yv))
    for rep in range(n_repeats):
        for tr, te in StratifiedKFold(5, shuffle=True,
                                      random_state=C.SEED + rep).split(Xv, yv):
            if len(np.unique(yv[tr])) < 2:
                continue
            m = Pipeline([
                ("sel", SelectKBest(f_classif, k=200)),
                ("clf", RandomForestClassifier(
                    n_estimators=400, min_samples_leaf=2, max_features="sqrt",
                    class_weight="balanced_subsample", random_state=C.SEED,
                    n_jobs=1))]).fit(Xv[tr], yv[tr])
            acc[te] += m.predict_proba(Xv[te])[:, 1]
            cnt[te] += 1
    seen = cnt > 0
    return float(roc_auc_score(yv[seen], (acc[seen] / cnt[seen])))


def main():
    rows, panels = [], {}
    for arm, label_name in PAIRS:
        delta, label = paired_frame(arm)
        score, genes = alignment_scores(delta, label)
        a = score[label.values == 1].dropna()
        b = score[label.values == 0].dropna()
        if len(a) < 3 or len(b) < 3:
            continue
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        r = 2 * u / (len(a) * len(b)) - 1
        auc = roc_auc_score(label.loc[score.dropna().index].values,
                            -score.dropna().values)
        auc_model = delta_classifier(delta, label)
        rows.append({
            "comparison": f"Diagnosis to {label_name}",
            "n_subjects": int(len(score.dropna())),
            "n_unfavourable": int(len(a)), "n_cured": int(len(b)),
            "median_unfavourable": float(a.median()),
            "median_cured": float(b.median()),
            "rank_biserial_r": float(r), "p_value": float(p),
            "roc_auc_low_alignment": float(auc),
            "roc_auc_delta_model": auc_model,
            "genes_in_reference": len(genes)})
        print(f"  classifier on the change vectors: AUC = {auc_model:.3f}")
        panels[arm] = (score, label, label_name)
        print(f"\n=== Diagnosis to {label_name} ===")
        print(f"  paired subjects: {len(score.dropna())} "
              f"({len(a)} unfavourable, {len(b)} cured)")
        print(f"  median alignment  cured {b.median():+.3f} vs "
              f"unfavourable {a.median():+.3f}")
        print(f"  Mann-Whitney p = {p:.4f}, rank-biserial r = {r:+.2f}")
        print(f"  AUC using low alignment as the risk score = {auc:.3f}")

    out = pd.DataFrame(rows)
    out.to_csv(f"{C.TAB}/response_trajectory.csv", index=False)

    fig, axes = plt.subplots(1, len(panels), figsize=(4.3 * len(panels), 4.6),
                             sharey=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (arm, (score, label, nice)) in zip(axes, panels.items()):
        groups = [score[label.values == 0].dropna().values,
                  score[label.values == 1].dropna().values]
        parts = ax.violinplot(groups, positions=[0, 1], widths=0.75,
                              showextrema=False)
        for k, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(["#4C72B0", "#C44E52"][k])
            pc.set_alpha(0.45)
        for k, g in enumerate(groups):
            ax.scatter(np.random.default_rng(C.SEED + k).normal(k, 0.055, len(g)),
                       g, s=22, color=["#2F4B7C", "#8C2F33"][k], alpha=0.85,
                       zorder=3, linewidths=0)
            ax.hlines(np.median(g), k - 0.28, k + 0.28, color="black", lw=2,
                      zorder=4)
        r = out[out.comparison == f"Diagnosis to {nice}"].iloc[0]
        ax.set_title(f"Diagnosis to {nice}\n"
                     f"p = {r.p_value:.3f}, r = {r.rank_biserial_r:+.2f}",
                     fontsize=11, fontweight="bold")
        ax.set_xticks([0, 1])
        ax.set_xticklabels([f"Cured\n(n={len(groups[0])})",
                            f"Unfavourable\n(n={len(groups[1])})"], fontsize=9)
        ax.axhline(0, color="#999999", lw=0.8, ls=":")
    axes[0].set_ylabel("Alignment with the cured-response direction\n"
                       "(cosine similarity)", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_response_trajectory.png", dpi=300)
    plt.close(fig)

    print("\n" + out.to_string(index=False))
    with open(f"{C.TAB}/response_trajectory.json", "w") as fh:
        json.dump(out.to_dict("records"), fh, indent=2)
    print("\nwrote response_trajectory.csv and Figure_response_trajectory.png")


if __name__ == "__main__":
    main()
