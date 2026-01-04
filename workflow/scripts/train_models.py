import json, numpy as np, pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import joblib

try:
    import xgboost as xgb
except Exception:
    xgb = None

cfg = snakemake.config
seed = int(cfg.get("random_seed", 0))

X = pd.read_parquet(snakemake.input["X"])
y = pd.read_parquet(snakemake.input["y"])
meta = pd.read_parquet(snakemake.input["meta"])
df = X.merge(y, on="sample_id", how="inner").merge(meta, on="sample_id", how="inner")

val_cohort = cfg.get("external_validation_cohort")

# If no external validation cohort, use all data for training
if val_cohort is None or val_cohort == "null":
    print("INFO: No external validation cohort. Using all data for nested CV.")
    train_df = df.copy()
else:
    print(f"INFO: Holding out {val_cohort} for external validation.")
    train_df = df[df["cohort_id"] != val_cohort].copy()

feature_cols = [c for c in train_df.columns if c not in ("sample_id","label","cohort_id","run_accession","platform","timepoint","title","characteristics","supplementary_file")]
Xmat = train_df[feature_cols].to_numpy()
yvec = train_df["label"].astype(int).to_numpy()

print(f"Training samples: {len(yvec)}")
print(f"Class distribution: {np.bincount(yvec)}")

outer = StratifiedKFold(n_splits=int(cfg["nested_cv"]["outer_folds"]), shuffle=True, random_state=seed)
inner = StratifiedKFold(n_splits=int(cfg["nested_cv"]["inner_folds"]), shuffle=True, random_state=seed)

def fold_metrics(y_true, y_prob):
    return {"roc_auc": float(roc_auc_score(y_true, y_prob)),
            "pr_auc": float(average_precision_score(y_true, y_prob))}

cands = []
logit = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000, random_state=seed, class_weight='balanced'))])
# Reduced grid: C=1.0 is usually decent
cands.append(("logistic", logit, {"clf__C":[1.0]}))

rf = RandomForestClassifier(random_state=seed, n_jobs=4, class_weight='balanced')
# Reduced grid: 100 trees is enough for pilot
cands.append(("random_forest", rf, {"n_estimators":[100], "max_depth":[10], "min_samples_leaf":[2]}))

if xgb is not None:
    # Estimate outcome ratio for XGBoost
    neg, pos = np.bincount(yvec)
    spw = float(neg) / pos
    # Reduced grid
    xgbc = xgb.XGBClassifier(random_state=seed, n_jobs=4, eval_metric="logloss", tree_method="hist", scale_pos_weight=spw)
    cands.append(("xgboost", xgbc, {"max_depth":[3], "n_estimators":[100], "learning_rate":[0.1], "subsample":[0.8]}))

results = []
best_models = {}
for name, est, grid in cands:
    fstats=[]
    for tr, te in outer.split(Xmat, yvec):
        gs = GridSearchCV(est, grid, cv=inner, scoring="roc_auc", n_jobs=4)
        gs.fit(Xmat[tr], yvec[tr])
        best = gs.best_estimator_
        yprob = best.predict_proba(Xmat[te])[:,1] if hasattr(best,"predict_proba") else best.decision_function(Xmat[te])
        if yprob.max()>1 or yprob.min()<0:
            yprob = (yprob - yprob.min())/(yprob.max()-yprob.min()+1e-9)
        fstats.append(fold_metrics(yvec[te], yprob))
    results.append({"model": name, "fold_metrics": fstats})

    gs_all = GridSearchCV(est, grid, cv=inner, scoring="roc_auc", n_jobs=4)
    gs_all.fit(Xmat, yvec)
    best_models[name] = gs_all.best_estimator_

def mean_auc(e): return float(np.mean([m["roc_auc"] for m in e["fold_metrics"]]))
best_entry = sorted(results, key=mean_auc, reverse=True)[0]
best_name = best_entry["model"]

bundle = {"best_model_name": best_name, "best_model": best_models[best_name], "feature_cols": feature_cols, "config": cfg}
Path("outputs/models").mkdir(parents=True, exist_ok=True)
with open(snakemake.output[0], "w", encoding="utf-8") as f:
    json.dump({"models": results, "selected": best_entry}, f, indent=2)
joblib.dump(bundle, snakemake.output[1])
