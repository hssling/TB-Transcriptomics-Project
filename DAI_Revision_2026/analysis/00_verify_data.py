"""WP-0: Verify data structure for the DAI revision.
Establishes: modeling samples, subject mapping, baseline definition,
failure count in modeling set, and available covariate proxies.
"""
import re
import pandas as pd

ROOT = "d:/research-automation/TB multiomics/TB-Treatment-Failure-Clean"
feat = pd.read_parquet(f"{ROOT}/outputs/dataset/feature_matrix.parquet")
labels = pd.read_parquet(f"{ROOT}/outputs/dataset/labels.parquet")
meta = pd.read_parquet(f"{ROOT}/outputs/dataset/metadata.parquet")

print("feat:", feat.shape, "| labels:", labels.shape, "| meta:", meta.shape)


def parse(s, key):
    if not isinstance(s, str):
        return None
    m = re.search(rf"{key}:\s*([^|]+)", s)
    return m.group(1).strip() if m else None


for k in ["treatmentresult", "subject", "time", "tissue", "disease state",
          "timetonegativity", "mgit", "xpert", "tgrv", "Sex", "gender", "hiv",
          "diabetes", "drug", "resistance"]:
    meta[k.replace(" ", "_")] = meta["characteristics"].apply(lambda s: parse(s, k))

print("\n-- timepoints (parsed 'time') --")
print(meta["time"].value_counts(dropna=False).head(20))
print("\n-- treatmentresult --")
print(meta["treatmentresult"].value_counts(dropna=False))

# Map labels onto modeling samples
modeling_ids = set(feat["sample_id"])
mm = meta[meta["sample_id"].isin(modeling_ids)].copy()
lab_map = dict(zip(labels["sample_id"], labels["label"]))
mm["label"] = mm["sample_id"].map(lab_map)
print("\n-- modeling samples:", mm.shape[0], "--")
print("label dist in modeling set:")
print(mm["label"].value_counts(dropna=False))
print("\ntreatmentresult in modeling set:")
print(mm["treatmentresult"].value_counts(dropna=False))
print("\ntime in modeling set:")
print(mm["time"].value_counts(dropna=False).head(20))
print("\nunique subjects in modeling set:", mm["subject"].nunique())
print("subjects with >1 sample:",
      (mm.groupby("subject").size() > 1).sum())

# failures per subject
fail_subj = mm.loc[mm["label"] == 1, "subject"].nunique()
print("unique FAILURE subjects in modeling set:", fail_subj)

# Covariate availability
print("\n-- covariate non-null counts (modeling set) --")
for c in ["mgit", "xpert", "tgrv", "timetonegativity", "Sex", "gender",
          "hiv", "diabetes", "drug", "resistance"]:
    print(f"  {c}: {mm[c].notna().sum()} non-null; sample vals:",
          list(pd.Series(mm[c].dropna().unique())[:4]))

mm.to_csv(f"{ROOT}/DAI_Revision_2026/tables/modeling_metadata.csv", index=False)
print("\nsaved modeling_metadata.csv")
