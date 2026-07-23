"""Discrimination of unfavourable outcome within each biological state.

One modelling protocol is applied to every arm so that arms are directly
comparable. Feature pre-selection sits inside the cross-validation loop, so no
information crosses the train/test boundary. The combined arm uses
subject-grouped folds and exists for contrast only: it mixes two biological
states and is not offered as a prediction result.

Reported per arm and per class: sensitivity, specificity, predictive values,
F1, plus ROC-AUC, precision-recall AUC, Matthews correlation coefficient,
balanced accuracy, Brier score and a label-permutation null.
"""
import argparse
import json
import warnings

import common2 as C

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import (LeaveOneOut, RepeatedStratifiedKFold,
                                     StratifiedGroupKFold, StratifiedKFold)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

K_FEATURES = 200
N_REPEATS = 40
N_PERM = 500
N_BOOT = 2000
rng = np.random.default_rng(C.SEED)


def make_model(name, y, light=False):
    """Model definitions. `light` halves ensemble size for the permutation
    protocol, which applies the same configuration to observed and permuted
    labels so the comparison stays internally consistent."""
    spw = (y == 0).sum() / max(1, (y == 1).sum())
    sel = SelectKBest(f_classif, k=K_FEATURES)
    if name == "logistic_regression":
        est = LogisticRegression(penalty="l2", C=0.1, max_iter=5000,
                                 class_weight="balanced")
        return Pipeline([("sel", sel), ("sc", StandardScaler()), ("clf", est)])
    if name == "random_forest":
        est = RandomForestClassifier(n_estimators=100 if light else 400,
                                     min_samples_leaf=2,
                                     max_features="sqrt",
                                     class_weight="balanced_subsample",
                                     random_state=C.SEED, n_jobs=1)
        return Pipeline([("sel", sel), ("clf", est)])
    if name == "gradient_boosting":
        est = XGBClassifier(n_estimators=80 if light else 200, max_depth=3,
                            learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.6,
                            scale_pos_weight=spw, eval_metric="logloss",
                            random_state=C.SEED, n_jobs=1, verbosity=0)
        return Pipeline([("sel", sel), ("clf", est)])
    raise ValueError(name)


def cv_oof(X, y, name, groups=None, n_repeats=N_REPEATS, seed=C.SEED,
           light=False):
    """Pooled out-of-fold probabilities, averaged over repeats."""
    Xv, yv = X.values, y.values
    acc = np.zeros(len(yv))
    cnt = np.zeros(len(yv))
    for rep in range(n_repeats):
        if groups is None:
            splitter = StratifiedKFold(5, shuffle=True, random_state=seed + rep)
            folds = splitter.split(Xv, yv)
        else:
            splitter = StratifiedGroupKFold(5, shuffle=True,
                                            random_state=seed + rep)
            folds = splitter.split(Xv, yv, groups)
        for tr, te in folds:
            if len(np.unique(yv[tr])) < 2:
                continue
            m = make_model(name, yv[tr], light=light).fit(Xv[tr], yv[tr])
            acc[te] += m.predict_proba(Xv[te])[:, 1]
            cnt[te] += 1
    seen = cnt > 0
    p = np.full(len(yv), np.nan)
    p[seen] = acc[seen] / cnt[seen]
    return p, seen


def class_metrics(y, pred):
    """Sensitivity, specificity and predictive values reported for each class."""
    rows = []
    for c in (0, 1):
        yc = (y == c).astype(int)
        pc = (pred == c).astype(int)
        tn, fp, fn, tp = confusion_matrix(yc, pc, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) else np.nan
        spec = tn / (tn + fp) if (tn + fp) else np.nan
        ppv = tp / (tp + fp) if (tp + fp) else np.nan
        npv = tn / (tn + fn) if (tn + fn) else np.nan
        f1 = 2 * ppv * sens / (ppv + sens) if (ppv and sens) else 0.0
        rows.append({"class": "Unfavourable" if c else "Cured",
                     "n": int((y == c).sum()),
                     "sensitivity": sens, "specificity": spec,
                     "ppv": ppv, "npv": npv, "f1": f1})
    return rows


def youden_threshold(y, p):
    order = np.unique(p)
    best, thr = -np.inf, 0.5
    for t in order:
        pred = (p >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        sens = tp / (tp + fn) if (tp + fn) else 0
        spec = tn / (tn + fp) if (tn + fp) else 0
        if sens + spec - 1 > best:
            best, thr = sens + spec - 1, t
    return thr


def boot_ci(y, p, fn, n=N_BOOT):
    vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if len(np.unique(y[b])) < 2:
            continue
        vals.append(fn(y[b], p[b]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def evaluate(X, y, name, groups=None):
    p, seen = cv_oof(X, y, name, groups)
    yv, pv = y.values[seen], p[seen]
    auc = roc_auc_score(yv, pv)
    ap = average_precision_score(yv, pv)
    thr = youden_threshold(yv, pv)
    pred = (pv >= thr).astype(int)
    tn, fp, fn_, tp = confusion_matrix(yv, pred, labels=[0, 1]).ravel()
    mcc_num = tp * tn - fp * fn_
    mcc_den = np.sqrt(float((tp + fp) * (tp + fn_) * (tn + fp) * (tn + fn_)))
    res = {
        "model": name,
        "n": int(len(yv)),
        "n_events": int(yv.sum()),
        "prevalence": float(yv.mean()),
        "roc_auc": float(auc),
        "roc_auc_ci": boot_ci(yv, pv, roc_auc_score),
        "pr_auc": float(ap),
        "pr_auc_ci": boot_ci(yv, pv, average_precision_score),
        "threshold": float(thr),
        "balanced_accuracy": float(((tp / (tp + fn_)) + (tn / (tn + fp))) / 2),
        "mcc": float(mcc_num / mcc_den) if mcc_den else 0.0,
        "brier": float(brier_score_loss(yv, pv)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn_), "tp": int(tp)},
        "per_class": class_metrics(yv, pred),
    }
    return res, p, seen


def permutation_null(X, y, name, groups=None, n_perm=N_PERM):
    """Observed and null AUC under one shared, inexpensive CV protocol."""
    def one(labels):
        pp, ss = cv_oof(X, pd.Series(labels, index=y.index), name,
                        groups, n_repeats=1, seed=C.SEED, light=True)
        return roc_auc_score(labels[ss], pp[ss])

    obs = one(y.values)
    null = []
    for i in range(n_perm):
        perm = rng.permutation(y.values)
        if len(np.unique(perm)) < 2:
            continue
        null.append(one(perm))
    null = np.array(null)
    p = float((np.sum(null >= obs) + 1) / (len(null) + 1))
    return {"observed_auc": float(obs), "null_mean": float(null.mean()),
            "null_sd": float(null.std()), "n_perm": int(len(null)),
            "permutation_p": p}


def loo_auc(X, y, name):
    Xv, yv = X.values, y.values
    p = np.zeros(len(yv))
    for tr, te in LeaveOneOut().split(Xv):
        m = make_model(name, yv[tr]).fit(Xv[tr], yv[tr])
        p[te] = m.predict_proba(Xv[te])[:, 1]
    return float(roc_auc_score(yv, p))


def run_arm(arm):
    models = ["logistic_regression", "random_forest", "gradient_boosting"]
    summary = {}
    oof_frames = []

    for arm in [arm]:
        X, y, meta = C.load_arm(arm)
        groups = meta["subject"].values if arm == "combined" else None
        print(f"\n=== {arm}: n={len(y)} events={int(y.sum())} ===", flush=True)
        arm_res = {"arm": arm, "label": C.ARM_LABEL[arm],
                   "n": int(len(y)), "n_events": int(y.sum()),
                   "n_subjects": int(meta["subject"].nunique()),
                   "models": {}}
        best_name, best_auc, best_p, best_seen = None, -1, None, None
        for name in models:
            res, p, seen = evaluate(X, y, name, groups)
            arm_res["models"][name] = res
            print(f"  {name:22s} AUC={res['roc_auc']:.3f} "
                  f"CI={res['roc_auc_ci'][0]:.2f}-{res['roc_auc_ci'][1]:.2f} "
                  f"PR-AUC={res['pr_auc']:.3f} MCC={res['mcc']:.2f}", flush=True)
            if res["roc_auc"] > best_auc:
                best_name, best_auc, best_p, best_seen = name, res["roc_auc"], p, seen
        arm_res["best_model"] = best_name
        arm_res["permutation"] = permutation_null(X, y, best_name, groups)
        print(f"  permutation ({best_name}): obs={arm_res['permutation']['observed_auc']:.3f} "
              f"null={arm_res['permutation']['null_mean']:.3f} "
              f"p={arm_res['permutation']['permutation_p']:.3f}", flush=True)
        if arm != "combined":
            arm_res["loo_auc"] = loo_auc(X, y, best_name)
            print(f"  leave-one-out AUC = {arm_res['loo_auc']:.3f}", flush=True)
        summary[arm] = arm_res

        oof_frames.append(pd.DataFrame({
            "sample_code": X.index[best_seen], "arm": arm,
            "subject": meta["subject"].values[best_seen],
            "label": y.values[best_seen], "pred_prob": best_p[best_seen],
            "model": best_name}))

    with open(f"{C.TAB}/arm_metrics_{arm}.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    pd.concat(oof_frames).to_csv(f"{C.TAB}/arm_oof_{arm}.csv", index=False)
    print(f"\nwrote arm_metrics_{arm}.json and arm_oof_{arm}.csv")


def merge():
    """Combine the per-arm shards into the two files the rest of the
    pipeline consumes."""
    summary, frames = {}, []
    for arm in C.ARMS + ["combined"]:
        with open(f"{C.TAB}/arm_metrics_{arm}.json") as fh:
            summary.update(json.load(fh))
        frames.append(pd.read_csv(f"{C.TAB}/arm_oof_{arm}.csv"))
    with open(f"{C.TAB}/arm_metrics.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    pd.concat(frames).to_csv(f"{C.TAB}/arm_oof_predictions.csv", index=False)
    print("merged arm_metrics.json and arm_oof_predictions.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=C.ARMS + ["combined"])
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.merge:
        merge()
    elif args.arm:
        run_arm(args.arm)
    else:
        for a in C.ARMS + ["combined"]:
            run_arm(a)
        merge()
