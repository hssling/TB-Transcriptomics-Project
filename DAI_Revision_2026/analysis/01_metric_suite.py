"""WP-A: Full predictive-performance metric suite on the leakage-free
BASELINE (DX-only, one-per-subject) cohort.

Addresses R1.7 (ROC text vs figure), R2.1 (class distribution in Methods),
R2.2 (precision/recall/F1/confusion matrix/PR curve at operating threshold),
and the timepoint-leakage problem (subject == sample at baseline).

Design: RepeatedStratifiedKFold out-of-fold (OOF) probabilities pooled per
sample; metrics computed on pooled OOF; bootstrap 95% CIs by resampling
samples. Univariate SelectKBest performed INSIDE each fold (no leakage).
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             roc_curve, precision_recall_curve, brier_score_loss,
                             confusion_matrix, f1_score, matthews_corrcoef,
                             precision_score, recall_score, balanced_accuracy_score)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
import common

RNG = 20260613
OUT_FIG = f"{common.ROOT}/DAI_Revision_2026/figures"
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

X, y, meta = common.load_baseline()
Xv = X.values
yv = y.values
print(f"Baseline cohort: N={len(y)}, failures={yv.sum()}, cures={(yv==0).sum()}, "
      f"prevalence={yv.mean():.3f}")

K = 200  # univariate pre-selection size inside each fold
spw = (yv == 0).sum() / max(1, (yv == 1).sum())

models = {
    "Logistic_L2": Pipeline([
        ("sel", SelectKBest(f_classif, k=K)), ("sc", StandardScaler()),
        ("clf", LogisticRegression(penalty="l2", C=0.1, class_weight="balanced",
                                   max_iter=2000, solver="liblinear"))]),
    "RandomForest": Pipeline([
        ("sel", SelectKBest(f_classif, k=K)),
        ("clf", RandomForestClassifier(n_estimators=400, max_depth=4,
                                       class_weight="balanced_subsample",
                                       random_state=RNG, n_jobs=-1))]),
    "XGBoost": Pipeline([
        ("sel", SelectKBest(f_classif, k=K)),
        ("clf", XGBClassifier(n_estimators=120, max_depth=3, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.6,
                              scale_pos_weight=spw, eval_metric="logloss",
                              random_state=RNG, n_jobs=-1))]),
}

N_REPEATS = 40
rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=N_REPEATS, random_state=RNG)

oof = {m: np.zeros(len(yv)) for m in models}
counts = np.zeros(len(yv))
for tr, te in rskf.split(Xv, yv):
    counts[te] += 1
    for name, pipe in models.items():
        pipe.fit(Xv[tr], yv[tr])
        oof[name][te] += pipe.predict_proba(Xv[te])[:, 1]
for name in models:
    oof[name] /= counts  # mean OOF prob per sample across repeats


def boot_ci(metric_fn, y_true, y_score, n=2000, seed=RNG):
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y_true))
    vals = []
    for _ in range(n):
        s = rng.choice(idx, len(idx), replace=True)
        if len(np.unique(y_true[s])) < 2:
            continue
        try:
            vals.append(metric_fn(y_true[s], y_score[s]))
        except Exception:
            pass
    return float(np.mean(vals)), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


summary = {}
for name in models:
    s = oof[name]
    auc = roc_auc_score(yv, s)
    ap = average_precision_score(yv, s)
    _, auc_lo, auc_hi = boot_ci(roc_auc_score, yv, s)
    _, ap_lo, ap_hi = boot_ci(average_precision_score, yv, s)
    summary[name] = {"roc_auc": auc, "roc_auc_ci95": [auc_lo, auc_hi],
                     "pr_auc": ap, "pr_auc_ci95": [ap_lo, ap_hi],
                     "brier": brier_score_loss(yv, s)}
    print(f"{name:14s} ROC-AUC={auc:.3f} [{auc_lo:.3f},{auc_hi:.3f}]  "
          f"PR-AUC={ap:.3f} [{ap_lo:.3f},{ap_hi:.3f}]  Brier={summary[name]['brier']:.3f}")

best = max(summary, key=lambda m: summary[m]["roc_auc"])
print(f"\nBest model: {best}")
sb = oof[best]

# Operating threshold: maximize Youden's J (sensitivity+specificity-1)
fpr, tpr, thr = roc_curve(yv, sb)
J = tpr - fpr
opt = int(np.argmax(J))
thr_opt = float(thr[opt])
pred = (sb >= thr_opt).astype(int)
cm = confusion_matrix(yv, pred)
tn, fp, fn, tp = cm.ravel()
op = {
    "threshold": thr_opt,
    "sensitivity_recall": recall_score(yv, pred),
    "specificity": tn / (tn + fp),
    "precision_ppv": precision_score(yv, pred, zero_division=0),
    "npv": tn / (tn + fn) if (tn + fn) else None,
    "f1": f1_score(yv, pred, zero_division=0),
    "mcc": matthews_corrcoef(yv, pred),
    "balanced_accuracy": balanced_accuracy_score(yv, pred),
    "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
}
print("Operating point (Youden J):", json.dumps(op, indent=2))

results = {"cohort": "GSE89403 baseline (DX-only, one per subject)",
           "n": int(len(yv)), "failures": int(yv.sum()), "cures": int((yv == 0).sum()),
           "prevalence": float(yv.mean()), "cv": f"RepeatedStratifiedKFold 5x{N_REPEATS}",
           "models": summary, "best_model": best, "operating_point": op}
with open(f"{OUT_TAB}/wpA_metric_suite.json", "w") as f:
    json.dump(results, f, indent=2)

# OOF predictions table
pd.DataFrame({"sample_id": X.index, "y_true": yv,
              **{f"oof_{m}": oof[m] for m in models}}).to_csv(
    f"{OUT_TAB}/wpA_oof_predictions.csv", index=False)

# ---- Figures: ROC, PR, calibration, confusion (best model) ----
fig, ax = plt.subplots(2, 2, figsize=(11, 9))
# ROC
for name in models:
    f, t, _ = roc_curve(yv, oof[name])
    ax[0, 0].plot(f, t, lw=2,
                  label=f"{name} (AUC={summary[name]['roc_auc']:.2f})")
ax[0, 0].plot([0, 1], [0, 1], "k--", lw=1)
ax[0, 0].set_xlabel("1 - Specificity", fontsize=13)
ax[0, 0].set_ylabel("Sensitivity", fontsize=13)
ax[0, 0].set_title("A  ROC (pooled out-of-fold)", fontsize=14, loc="left")
ax[0, 0].legend(fontsize=10)
# PR
for name in models:
    p, r, _ = precision_recall_curve(yv, oof[name])
    ax[0, 1].plot(r, p, lw=2,
                  label=f"{name} (AP={summary[name]['pr_auc']:.2f})")
ax[0, 1].axhline(yv.mean(), color="k", ls="--", lw=1,
                 label=f"Prevalence={yv.mean():.2f}")
ax[0, 1].set_xlabel("Recall", fontsize=13)
ax[0, 1].set_ylabel("Precision", fontsize=13)
ax[0, 1].set_title("B  Precision-Recall", fontsize=14, loc="left")
ax[0, 1].legend(fontsize=10)
# Calibration
from sklearn.calibration import calibration_curve
frac, mean_pred = calibration_curve(yv, sb, n_bins=5, strategy="quantile")
ax[1, 0].plot(mean_pred, frac, "o-", lw=2, color="#cc3333")
ax[1, 0].plot([0, 1], [0, 1], "k--", lw=1)
ax[1, 0].set_xlabel("Mean predicted probability", fontsize=13)
ax[1, 0].set_ylabel("Observed failure fraction", fontsize=13)
ax[1, 0].set_title(f"C  Calibration — {best} (Brier={summary[best]['brier']:.2f})",
                   fontsize=13, loc="left")
# Confusion
im = ax[1, 1].imshow(cm, cmap="Blues")
for (i, j), v in np.ndenumerate(cm):
    ax[1, 1].text(j, i, str(v), ha="center", va="center", fontsize=18,
                  color="white" if v > cm.max() / 2 else "black")
ax[1, 1].set_xticks([0, 1]); ax[1, 1].set_yticks([0, 1])
ax[1, 1].set_xticklabels(["Pred Cure (0)", "Pred Failure (1)"], fontsize=11)
ax[1, 1].set_yticklabels(["True Cure (0)", "True Failure (1)"], fontsize=11)
ax[1, 1].set_title(f"D  Confusion @Youden (Sens={op['sensitivity_recall']:.2f}, "
                   f"Spec={op['specificity']:.2f})", fontsize=12, loc="left")
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure1_performance.png", dpi=300)
plt.close()
print("\nSaved Figure1_performance.png and wpA_* tables")
