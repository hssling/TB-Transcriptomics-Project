"""Adversarial checks on the week-24 result before it is relied upon.

The end-of-treatment arm carries the study's only positive finding, so it is
the one that must survive attack. Five things could produce it artefactually:

  1  technical confounding — library size or detection rate differing by outcome
  2  a handful of influential subjects
  3  selection of the best of three classifiers before testing it
  4  testing four arms and reporting the one that reached significance
  5  residual bacterial load, making the signature a proxy for active disease

Each is tested here. Failures are reported, not smoothed.
"""
import json
import warnings

import common2 as C

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")

K = 200
N_REPEATS = 20
SEED = C.SEED


def model():
    return Pipeline([
        ("sel", SelectKBest(f_classif, k=K)),
        ("clf", RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                       max_features="sqrt",
                                       class_weight="balanced_subsample",
                                       random_state=SEED, n_jobs=1))])


def oof(X, y, n_repeats=N_REPEATS, seed=SEED):
    Xv, yv = X.values, y.values
    acc, cnt = np.zeros(len(yv)), np.zeros(len(yv))
    for rep in range(n_repeats):
        for tr, te in StratifiedKFold(5, shuffle=True,
                                      random_state=seed + rep).split(Xv, yv):
            if len(np.unique(yv[tr])) < 2:
                continue
            m = model().fit(Xv[tr], yv[tr])
            acc[te] += m.predict_proba(Xv[te])[:, 1]
            cnt[te] += 1
    seen = cnt > 0
    p = np.full(len(yv), np.nan)
    p[seen] = acc[seen] / cnt[seen]
    return p, seen


def check_technical(report):
    """1. Do library size or detection rate differ by outcome?"""
    print("\n=== 1. Technical confounding ===")
    counts = pd.read_csv(f"{C.ROOT}/external/GSE89403_rawCounts_GeneNames_"
                         "AllSamples.csv.gz", index_col=0)
    counts = counts.drop(columns=["symbol"])
    rows = []
    for arm in C.ARMS:
        X, y, meta = C.load_arm(arm)
        ids = [s for s in X.index if s in counts.columns]
        lib = counts[ids].sum(axis=0)
        det = (counts[ids] > 0).mean(axis=0)
        lab = y.loc[ids].values
        for name, v in [("library size", lib), ("detection rate", det)]:
            a, b = v[lab == 1], v[lab == 0]
            _, p = mannwhitneyu(a, b, alternative="two-sided")
            rows.append({"arm": C.ARM_LABEL[arm], "metric": name,
                         "median_unfavourable": float(np.median(a)),
                         "median_cured": float(np.median(b)),
                         "p_value": float(p)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    report["technical"] = t.to_dict("records")
    worst = t.loc[t.p_value.idxmin()]
    print(f"  -> smallest p across all technical comparisons: {worst.p_value:.3f}")
    return t


def check_influence(report):
    """2. Is week-24 discrimination carried by a few subjects?"""
    print("\n=== 2. Influence of individual subjects (week 24) ===")
    X, y, meta = C.load_arm("week_24")
    base_p, seen = oof(X, y)
    base = roc_auc_score(y.values[seen], base_p[seen])
    print(f"  full-cohort AUC (20 repeats): {base:.3f}")

    rows = []
    for subj in sorted(meta.loc[y.values == 1, "subject"].unique()):
        keep = meta["subject"] != subj
        p, s = oof(X[keep.values], y[keep.values])
        auc = roc_auc_score(y[keep.values].values[s], p[s])
        rows.append({"subject_removed": subj, "outcome": "unfavourable",
                     "auc": float(auc), "delta": float(auc - base)})
        print(f"  drop unfavourable subject {subj:>4}: AUC {auc:.3f} "
              f"({auc - base:+.3f})")
    t = pd.DataFrame(rows)
    report["influence"] = {"baseline_auc": float(base),
                           "leave_one_out": t.to_dict("records"),
                           "min_auc": float(t.auc.min()),
                           "max_abs_delta": float(t.delta.abs().max())}
    print(f"  -> worst case after removing any single event: {t.auc.min():.3f}")
    return t


def check_model_selection(report):
    """3. Does the result depend on having picked the best classifier?"""
    print("\n=== 3. Sensitivity to classifier choice ===")
    metrics = json.load(open(f"{C.TAB}/arm_metrics.json"))
    rows = []
    for arm in C.ARMS:
        for name, res in metrics[arm]["models"].items():
            rows.append({"arm": C.ARM_LABEL[arm], "model": name,
                         "roc_auc": res["roc_auc"]})
    t = pd.DataFrame(rows)
    w = t[t.arm == "Week 24"]
    print(w.to_string(index=False))
    print(f"  -> week 24 range across classifiers: "
          f"{w.roc_auc.min():.3f}–{w.roc_auc.max():.3f}")
    report["model_selection"] = {
        "week24_min": float(w.roc_auc.min()),
        "week24_max": float(w.roc_auc.max()),
        "all_above_0.85": bool((w.roc_auc > 0.85).all())}
    return t


def check_multiplicity(report):
    """4. Does week 24 survive correction for testing four arms?"""
    print("\n=== 4. Multiplicity across arms ===")
    metrics = json.load(open(f"{C.TAB}/arm_metrics.json"))
    arms = C.ARMS
    praw = [metrics[a]["permutation"]["permutation_p"] for a in arms]
    rej_h, padj_h = multipletests(praw, method="holm")[:2]
    rej_b, padj_b = multipletests(praw, method="bonferroni")[:2]
    t = pd.DataFrame({"arm": [C.ARM_LABEL[a] for a in arms],
                      "p_raw": praw, "p_holm": padj_h,
                      "p_bonferroni": padj_b, "significant_holm": rej_h})
    print(t.to_string(index=False))
    report["multiplicity"] = t.to_dict("records")
    return t


def check_bacterial_load(report):
    """5. Is the week-24 signature a proxy for residual bacterial load?"""
    print("\n=== 5. Bacterial load at diagnosis vs week-24 prediction ===")
    X24, y24, m24 = C.load_arm("week_24")
    p, seen = oof(X24, y24)
    sub = m24.iloc[seen].copy()
    sub["pred"] = p[seen]
    rows = []
    for col in ["mgit", "xpert", "tgrv"]:
        v = pd.to_numeric(sub[col], errors="coerce")
        ok = v.notna()
        if ok.sum() < 20:
            continue
        rho, pv = spearmanr(sub.loc[ok, "pred"], v[ok])
        rows.append({"measure": col, "n": int(ok.sum()),
                     "spearman_rho": float(rho), "p_value": float(pv)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print("  note: these are diagnosis-time measures; the deposit carries no "
          "week-24 culture result, so residual load cannot be adjusted for "
          "directly.")
    report["bacterial_load"] = t.to_dict("records")
    return t


def main():
    report = {}
    check_technical(report)
    check_influence(report)
    check_model_selection(report)
    check_multiplicity(report)
    check_bacterial_load(report)
    with open(f"{C.TAB}/robustness_audit.json", "w") as fh:
        json.dump(report, fh, indent=2)
    print("\nwrote robustness_audit.json")


if __name__ == "__main__":
    main()
