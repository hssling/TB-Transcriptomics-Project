import pandas as pd
import numpy as np
from pathlib import Path

expr = pd.read_parquet(snakemake.input["expr"])
cohorts = pd.read_parquet(snakemake.input["cohorts"]).dropna(subset=["label"]).copy()

# CRITICAL: Filter for baseline samples ONLY to prevent data leakage
# We only want pre-treatment samples to predict treatment outcomes
if "timepoint" in cohorts.columns:
    baseline_cohorts = cohorts[cohorts["timepoint"] == "baseline"].copy()
    print(f"Filtered to baseline: {len(baseline_cohorts)}/{len(cohorts)} samples")
else:
    print("WARNING: No timepoint column found - using all samples")
    baseline_cohorts = cohorts.copy()

baseline_cohorts["label"] = baseline_cohorts["label"].astype(int)

# Filter samples BEFORE transposing to avoid pandas reindexing issues
X = expr.set_index("gene_id")
# Keep only samples that have labels
valid_samples = [col for col in X.columns if col in baseline_cohorts["sample_id"].values]
X = X.reindex(columns=valid_samples, fill_value=0)  # Use reindex to avoid KeyError
# Now transpose
X = X.T
X.index.name = "sample_id"

# Apply log1p transformation with robust NaN/inf handling
# Replace any NaNs or negative values with 0 before log1p
X = X.fillna(0.0).clip(lower=0)
X = np.log1p(X)
# Final cleanup: replace any NaN or inf values that might have been created
X = X.replace([np.inf, -np.inf], 0.0).fillna(0.0)

Path("outputs/dataset").mkdir(parents=True, exist_ok=True)
X.reset_index().to_parquet(snakemake.output[0], index=False)
baseline_cohorts[["sample_id","label"]].drop_duplicates().to_parquet(snakemake.output[1], index=False)
baseline_cohorts.drop(columns=["label"]).to_parquet(snakemake.output[2], index=False)
