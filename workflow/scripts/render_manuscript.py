import json
from pathlib import Path
import pandas as pd

with open(snakemake.input["ext"], "r", encoding="utf-8") as f:
    ext = json.load(f)
with open(snakemake.input["cv"], "r", encoding="utf-8") as f:
    cv = json.load(f)

top = pd.read_csv(snakemake.input["top"])
enrich = pd.read_csv(snakemake.input["enrich"])

Path("reports/manuscript").mkdir(parents=True, exist_ok=True)

top_list = ", ".join(top["feature"].head(10).tolist()) if "feature" in top.columns else "NA"

qmd = f'''---
title: "Whole-blood transcriptomic prediction of unfavourable TB treatment outcomes: multi-cohort development and external validation"
format: html
---

## Abstract
**Background:** Predicting unfavourable TB treatment outcomes at diagnosis remains challenging.  
**Methods:** We developed ML models using public whole-blood gene expression (training: GSE89403) and externally validated on an independent cohort (GSE193979). We used nested cross-validation and evaluated ROC AUC, PR AUC, and calibration.  
**Results:** External validation: cohort={ext.get("cohort")}, N={ext.get("n")}, events={ext.get("events")}, best model={ext.get("best_model_name")}. ROC AUC={ext.get("roc_auc")} (bootstrap mean={ext.get("roc_auc_bootstrap_mean")}, 95% CI={ext.get("roc_auc_ci95")}); PR AUC={ext.get("pr_auc")} (bootstrap mean={ext.get("pr_auc_bootstrap_mean")}, 95% CI={ext.get("pr_auc_ci95")}); Brier={ext.get("brier")}. Top features include: {top_list}.  
**Conclusions:** This reproducible pipeline demonstrates cross-cohort validation; additional prospective, standardized outcome definitions are needed prior to clinical use.

## Methods (pipeline summary)
- Metadata retrieval: GEOparse GSM annotations → cohort table with timepoint and outcome label rules.
- Ingestion: processed expression matrices (default) or raw FASTQ + Salmon (optional).
- Modeling: logistic regression, random forest, XGBoost; nested CV for tuning/evaluation.
- External validation: cohort-held-out evaluation with bootstrap CIs and calibration.

## Results
See:
- `outputs/models/nested_cv_metrics.json`
- `outputs/models/external_validation_metrics.json`
- Figures in `reports/figures/`

## Interpretation
Top features table: `reports/tables/top_features.csv`  
Enrichment: `reports/tables/enrichr_top_terms.csv`

## Limitations
- Outcome labels may be encoded differently across cohorts; label rules must be pre-specified and audited.
- Batch effects and platform differences may limit transferability.
- External validation event counts may be limited; confidence intervals should be interpreted accordingly.

## Data and code availability
All analyses are reproducible from this repository and the public GEO accessions.

'''
with open(snakemake.output[0], "w", encoding="utf-8") as f:
    f.write(qmd)
