import json, numpy as np, pandas as pd, joblib
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, average_precision_score, RocCurveDisplay
from sklearn.calibration import CalibrationDisplay
from sklearn.metrics import brier_score_loss
import sys

cfg = snakemake.config
seed = int(cfg.get("random_seed", 0))

X = pd.read_parquet(snakemake.input["X"])
y = pd.read_parquet(snakemake.input["y"])
meta = pd.read_parquet(snakemake.input["meta"])
bundle = joblib.load(snakemake.input["bundle"])

df = X.merge(y, on="sample_id", how="inner").merge(meta, on="sample_id", how="inner")
val_cohort = cfg.get("external_validation_cohort")

# If no external validation cohort specified, skip validation
if val_cohort is None or val_cohort == "null":
    print("INFO: No external validation cohort specified. Skipping external validation.")
    print("INFO: Model performance is reported via nested CV in train_models.py")
    metrics = {
        "cohort": None,
        "n": 0,
        "events": 0,
        "best_model_name": bundle["best_model_name"],
        "roc_auc": None, "roc_auc_bootstrap_mean": None, "roc_auc_ci95": [None, None],
        "pr_auc": None, "pr_auc_bootstrap_mean": None, "pr_auc_ci95": [None, None],
        "brier": None,
        "note": "External validation disabled - using nested CV only"
    }
    with open(snakemake.output[0], "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    
    # Create placeholder plots
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, "External Validation Disabled\nSee nested CV results in train_models.py", 
             ha='center', va='center', fontsize=14)
    plt.axis('off')
    plt.savefig(snakemake.output[1], dpi=200, bbox_inches="tight")
    plt.close()
    
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, "External Validation Disabled\nSee nested CV results in train_models.py", 
             ha='center', va='center', fontsize=14)
    plt.axis('off')
    plt.savefig(snakemake.output[2], dpi=200, bbox_inches="tight")
    plt.close()
    
    sys.exit(0)

val_df = df[df["cohort_id"] == val_cohort].copy()

Path("outputs/models").mkdir(parents=True, exist_ok=True)
Path("reports/figures").mkdir(parents=True, exist_ok=True)

if val_df.empty:
    print(f"WARNING: No samples found for validation cohort '{val_cohort}' (likely missing labels). Skipping validation.")
    metrics = {
        "cohort": val_cohort,
        "n": 0,
        "events": 0,
        "best_model_name": bundle["best_model_name"],
        "roc_auc": None, "roc_auc_bootstrap_mean": None, "roc_auc_ci95": [None, None],
        "pr_auc": None, "pr_auc_bootstrap_mean": None, "pr_auc_ci95": [None, None],
        "brier": None
    }
    with open(snakemake.output[0], "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    
    # Dummy plots
    plt.figure()
    plt.text(0.5, 0.5, "No Validation Data", ha='center', va='center')
    plt.savefig(snakemake.output[1])
    plt.close()
    
    plt.figure()
    plt.text(0.5, 0.5, "No Validation Data", ha='center', va='center')
    plt.savefig(snakemake.output[2])
    plt.close()
    
    sys.exit(0)

fc = bundle["feature_cols"]
model = bundle["best_model"]
Xv = val_df[fc].to_numpy()
yv = val_df["label"].astype(int).to_numpy()

yprob = model.predict_proba(Xv)[:,1] if hasattr(model,"predict_proba") else model.decision_function(Xv)
if yprob.max()>1 or yprob.min()<0:
    yprob = (yprob - yprob.min())/(yprob.max()-yprob.min()+1e-9)

def bootstrap_ci(metric_fn, y_true, y_score, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    stats=[]
    idx = np.arange(len(y_true))
    for _ in range(n):
        b = rng.choice(idx, size=len(idx), replace=True)
        # handle degenerate samples
        if len(np.unique(y_true[b])) < 2:
            continue
        stats.append(metric_fn(y_true[b], y_score[b]))
    stats = np.array(stats, dtype=float)
    if stats.size == 0:
        return None, None, None
    return float(np.mean(stats)), float(np.quantile(stats, 0.025)), float(np.quantile(stats, 0.975))

roc_mean, roc_lo, roc_hi = bootstrap_ci(roc_auc_score, yv, yprob, n=int(cfg["bootstrap"]["n"]), seed=int(cfg["bootstrap"]["seed"]))
pr_mean, pr_lo, pr_hi = bootstrap_ci(average_precision_score, yv, yprob, n=int(cfg["bootstrap"]["n"]), seed=int(cfg["bootstrap"]["seed"])+1)

brier = float(brier_score_loss(yv, yprob))

metrics = {
    "cohort": val_cohort,
    "n": int(len(yv)),
    "events": int(yv.sum()),
    "best_model_name": bundle["best_model_name"],
    "roc_auc": float(roc_auc_score(yv, yprob)) if len(np.unique(yv))>1 else None,
    "roc_auc_bootstrap_mean": roc_mean, "roc_auc_ci95": [roc_lo, roc_hi],
    "pr_auc": float(average_precision_score(yv, yprob)) if len(np.unique(yv))>1 else None,
    "pr_auc_bootstrap_mean": pr_mean, "pr_auc_ci95": [pr_lo, pr_hi],
    "brier": brier
}

with open(snakemake.output[0], "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

# ROC
plt.figure()
if len(np.unique(yv))>1:
    RocCurveDisplay.from_predictions(yv, yprob)
plt.title(f"External validation ROC: {val_cohort}")
plt.savefig(snakemake.output[1], dpi=200, bbox_inches="tight")
plt.close()

# Calibration
plt.figure()
if len(np.unique(yv))>1:
    CalibrationDisplay.from_predictions(yv, yprob, n_bins=10)
plt.title(f"External validation calibration: {val_cohort} (Brier={brier:.3f})")
plt.savefig(snakemake.output[2], dpi=200, bbox_inches="tight")
plt.close()
