"""WP-A sensitivity: proper SUBJECT-GROUPED CV across all timepoints.

Shows (a) the inflation caused by timepoint leakage in the original design,
and (b) that failure discrimination strengthens when on-treatment samples are
included - directly answering Reviewer 1's point that the signature 'will
probably be observed later in treatment' (R1.9). All folds keep a subject's
samples together (StratifiedGroupKFold) to prevent leakage.
"""
import json, warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
import re
warnings.filterwarnings("ignore")
import common

OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

# All-timepoint modeling set with subject + timepoint
feat = pd.read_parquet(f"{common.ROOT}/outputs/dataset/feature_matrix.parquet")
labels = pd.read_parquet(f"{common.ROOT}/outputs/dataset/labels.parquet")
meta = pd.read_parquet(f"{common.ROOT}/outputs/dataset/metadata.parquet")
def parse(s, k):
    if not isinstance(s, str): return None
    m = re.search(rf"{k}:\s*([^|]+)", s); return m.group(1).strip() if m else None
meta["subject"] = meta["characteristics"].apply(lambda s: parse(s, "subject"))
meta["time"] = meta["characteristics"].apply(lambda s: parse(s, "time"))
lab = dict(zip(labels["sample_id"], labels["label"]))
feat = feat.drop_duplicates("sample_id").set_index("sample_id")
meta = meta.drop_duplicates("sample_id").set_index("sample_id")
common_idx = feat.index.intersection(meta.index)
feat, meta = feat.loc[common_idx], meta.loc[common_idx]
gene_cols = [c for c in feat.columns if c.startswith("ENSG")]
X = feat[gene_cols].astype(float).values
y = np.array([lab.get(i, 0) for i in feat.index])
groups = meta["subject"].values

spw = (y == 0).sum() / max(1, (y == 1).sum())
pipe = Pipeline([("sel", SelectKBest(f_classif, k=200)),
                 ("clf", RandomForestClassifier(n_estimators=400, max_depth=4,
                  class_weight="balanced_subsample", random_state=20260613, n_jobs=-1))])

def grouped_oof(Xv, yv, grp, n_splits=5, repeats=10):
    oof = np.zeros(len(yv)); cnt = np.zeros(len(yv))
    for rep in range(repeats):
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=rep)
        for tr, te in sgkf.split(Xv, yv, grp):
            pipe.fit(Xv[tr], yv[tr])
            oof[te] += pipe.predict_proba(Xv[te])[:, 1]; cnt[te] += 1
    return oof / np.maximum(cnt, 1)

print("All-timepoint, SUBJECT-grouped (leakage-free) RandomForest:")
oof = grouped_oof(X, y, groups)
auc = roc_auc_score(y, oof); ap = average_precision_score(y, oof)
print(f"  N={len(y)} samples, {y.sum()} failure-samples, {len(set(groups))} subjects")
print(f"  ROC-AUC={auc:.3f}  PR-AUC={ap:.3f}")

# Per-timepoint discrimination (failure vs cure samples at each timepoint)
rows = []
for tp in ["DX", "day_7", "week_4", "week_24"]:
    mask = meta["time"].values == tp
    if mask.sum() > 5 and y[mask].sum() >= 2 and (y[mask] == 0).sum() >= 2:
        a = roc_auc_score(y[mask], oof[mask])
        rows.append({"timepoint": tp, "n": int(mask.sum()),
                     "failures": int(y[mask].sum()), "auc_oof": round(a, 3)})
tp_df = pd.DataFrame(rows)
print("\nDiscrimination by timepoint (pooled OOF):")
print(tp_df.to_string(index=False))

json.dump({"all_timepoint_grouped": {"roc_auc": auc, "pr_auc": ap,
          "n": int(len(y)), "failure_samples": int(y.sum())},
          "by_timepoint": rows},
          open(f"{OUT_TAB}/wpA_sensitivity_timepoints.json", "w"), indent=2)
print("\nSaved wpA_sensitivity_timepoints.json")
