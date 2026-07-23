"""Serialise the final model for each arm, so results can be inspected
without refitting.

Each arm's reported model is refitted on all of that arm's samples using the
same pipeline that was cross-validated, then written to disk together with the
feature list it selected, the metrics it produced, and the library versions it
was built under. A manifest records a SHA-256 for every artefact so that a
reader can confirm the file they load is the file described here.

Loading example:

    import joblib
    bundle = joblib.load("models/model_week_24.joblib")
    bundle["pipeline"].predict_proba(X)[:, 1]
"""
import hashlib
import json
import os
import platform
import sys
import warnings

import common2 as C

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

OUT = f"{C.ROOT}/models"
os.makedirs(OUT, exist_ok=True)
K_FEATURES = 200


def build(name, y):
    """Identical to the definitions cross-validated in 21_arm_models.py."""
    spw = (y == 0).sum() / max(1, (y == 1).sum())
    sel = SelectKBest(f_classif, k=K_FEATURES)
    if name == "logistic_regression":
        est = LogisticRegression(penalty="l2", C=0.1, max_iter=5000,
                                 class_weight="balanced")
        return Pipeline([("sel", sel), ("sc", StandardScaler()), ("clf", est)])
    if name == "random_forest":
        est = RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                     max_features="sqrt",
                                     class_weight="balanced_subsample",
                                     random_state=C.SEED, n_jobs=1)
        return Pipeline([("sel", sel), ("clf", est)])
    if name == "gradient_boosting":
        est = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.6,
                            scale_pos_weight=spw, eval_metric="logloss",
                            random_state=C.SEED, n_jobs=1, verbosity=0)
        return Pipeline([("sel", sel), ("clf", est)])
    raise ValueError(name)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    metrics = json.load(open(f"{C.TAB}/arm_metrics.json"))
    symbols = C.symbols()
    manifest = {
        "description": "Frozen models for each analytical arm of the "
                       "GSE89403 treatment-outcome analysis.",
        "caveat": "These models are refitted on all samples in their arm for "
                  "inspection. Reported discrimination comes from "
                  "cross-validation, not from these fits, and applying a model "
                  "to its own training data will overstate performance.",
        "seed": C.SEED,
        "n_features_selected": K_FEATURES,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "arms": {},
    }

    for arm in C.ARMS + ["combined"]:
        X, y, meta = C.load_arm(arm)
        name = metrics[arm]["best_model"]
        pipe = build(name, y.values).fit(X.values, y.values)

        idx = pipe.named_steps["sel"].get_support(indices=True)
        chosen = list(X.columns[idx])
        features = pd.DataFrame({
            "ensembl": chosen,
            "gene_symbol": [symbols.get(g, g) for g in chosen],
            "univariate_F": pipe.named_steps["sel"].scores_[idx]})
        features = features.sort_values("univariate_F", ascending=False)
        features.to_csv(f"{OUT}/features_{arm}.csv", index=False)

        bundle = {
            "arm": arm,
            "arm_label": C.ARM_LABEL[arm],
            "model_name": name,
            "pipeline": pipe,
            "feature_ensembl_ids": chosen,
            "gene_order": list(X.columns),
            "n_samples": int(len(y)),
            "n_events": int(y.sum()),
            "cross_validated_metrics": metrics[arm]["models"][name],
            "permutation": metrics[arm]["permutation"],
            "seed": C.SEED,
        }
        path = f"{OUT}/model_{arm}.joblib"
        joblib.dump(bundle, path, compress=3)

        manifest["arms"][arm] = {
            "label": C.ARM_LABEL[arm],
            "model": name,
            "file": f"models/model_{arm}.joblib",
            "features_file": f"models/features_{arm}.csv",
            "sha256": sha256(path),
            "bytes": os.path.getsize(path),
            "n_samples": int(len(y)),
            "n_events": int(y.sum()),
            "cross_validated_roc_auc": metrics[arm]["models"][name]["roc_auc"],
            "permutation_p": metrics[arm]["permutation"]["permutation_p"],
        }
        print(f"{C.ARM_LABEL[arm]:<15} {name:<20} "
              f"{os.path.getsize(path) / 1024:7.0f} KB  "
              f"CV AUC {metrics[arm]['models'][name]['roc_auc']:.3f}")

    with open(f"{OUT}/MANIFEST.json", "w") as fh:
        json.dump(manifest, fh, indent=2)

    # Round-trip check: a serialised model must load and score.
    print("\nverifying every artefact reloads and scores:")
    for arm in C.ARMS + ["combined"]:
        X, y, _ = C.load_arm(arm)
        b = joblib.load(f"{OUT}/model_{arm}.joblib")
        p = b["pipeline"].predict_proba(X.values[:3])[:, 1]
        assert np.isfinite(p).all(), arm
        print(f"  {arm:<10} ok  (first three predicted probabilities "
              f"{np.round(p, 3).tolist()})")

    print(f"\nwrote {len(manifest['arms'])} models and MANIFEST.json to {OUT}")


if __name__ == "__main__":
    main()
