# Reproducing the treatment-outcome analysis

Everything reported in *Whole-blood transcriptomic signatures of unfavourable
tuberculosis treatment outcome before and during therapy* is produced by the
scripts in `analysis/`. Raw data are downloaded from the NCBI Gene Expression
Omnibus on first run; nothing else is required.

## Environment

```
python >= 3.10
pip install -r requirements.txt
```

Built and tested with scikit-learn 1.8.0, XGBoost 3.1.2, SHAP 0.50.0,
statsmodels 0.14.6, pandas 2.x, numpy 2.x. Exact versions used for the frozen
models are recorded in `models/MANIFEST.json`.

On Windows hosts where the WMI service does not respond, `import sklearn`
can hang inside `platform.uname()`. `analysis/env_fix.py` disables that probe
and is imported by `analysis/common2.py` before scikit-learn. It is a no-op on
other platforms.

## Running the pipeline

Scripts are numbered in dependency order and are safe to run in sequence:

```
python analysis/20_build_full_dataset.py     # download GSE89403, build the matrix
python analysis/21_arm_models.py             # discrimination per arm  (slowest step)
python analysis/22_deconvolution_arms.py     # immune composition, correlation figure
python analysis/23_shap_arms.py              # SHAP attribution, model benchmark
python analysis/24_deg_arms.py               # differential expression, state partition
python analysis/25_enrichment.py             # pathway analysis
python analysis/26_network_shap.py           # conditional-dependency network
python analysis/27_external_gse67589.py      # independent cohort
python analysis/28_flowchart.py              # study flow diagram
python analysis/29_comparative.py            # performance and contrast figures
python analysis/30_confounders.py            # sex and bacterial-load audit
python analysis/31_robustness_audit.py       # adversarial checks on the week-24 arm
python analysis/32_response_trajectory.py    # within-subject treatment response
python analysis/33_established_signatures.py # published signatures, applied unfitted
python analysis/34_freeze_models.py          # serialise final models
```

`21_arm_models.py` takes roughly 40 minutes single-threaded because of the
permutation nulls. It accepts `--arm DX|day_7|week_4|week_24|combined` so the
five arms can be run in parallel, followed by `--merge`.

Random seeds are fixed throughout (`common2.SEED`). Documents are rebuilt from
the analysis outputs by the `build_*_v14.py` scripts, so no number in the
manuscript is typed by hand.

## What is committed

| Path | Contents |
| --- | --- |
| `analysis/` | All analysis scripts |
| `tables2/` | Every numeric result, as CSV and JSON |
| `figures2/` | Main and supplementary figures at 300 dpi |
| `data2/` | Processed expression matrix, sample table, gene map |
| `models/` | Frozen model per arm, selected features, manifest |
| `deliverables/` | Manuscript, supplementary, response and cover letters |

Raw GEO downloads are not committed. They are third-party data and the scripts
retrieve them reproducibly; `data2/` holds the processed matrix so results can
be checked without re-downloading.

## Frozen models

`models/model_<arm>.joblib` holds the fitted pipeline for each arm, the
features it selected, and the cross-validated metrics reported for it.
`models/MANIFEST.json` records a SHA-256 for every file plus the library
versions used.

```python
import joblib
bundle = joblib.load("models/model_week_24.joblib")
bundle["pipeline"].predict_proba(X)[:, 1]      # X: samples x genes, gene order in bundle["gene_order"]
```

Two caveats belong with these files. They are refitted on all samples in their
arm for inspection, so scoring them on their own training data will overstate
performance; the reported discrimination comes from cross-validation, in
`tables2/arm_metrics.json`. And `.joblib` files are Python pickles, which
execute code on load — verify the SHA-256 in `MANIFEST.json` before loading
these or any other pickle you did not create.

## Headline results

| Arm | n | Events | ROC-AUC (95% CI) | Permutation p | Genes at FDR < 0.05 |
| --- | --- | --- | --- | --- | --- |
| Pre-treatment | 90 | 7 | 0.65 (0.34–0.89) | 0.182 | 0 |
| Day 7 | 91 | 6 | 0.69 (0.56–0.82) | 0.202 | 0 |
| Week 4 | 92 | 8 | 0.60 (0.33–0.85) | 0.263 | 0 |
| Week 24 | 94 | 7 | 0.93 (0.81–1.00) | 0.006 | 5,924 |
| All timepoints | 367 | 28 | 0.68 (0.57–0.79) | 0.004 | — |

Two negative results are as important as the positive one and are reported as
such in the manuscript. Published signatures of active tuberculosis, applied
without fitting any parameter, matched or exceeded the fitted models in every
arm — so the machine learning added no predictive value. And the signature did
not transfer to an independent cohort (GSE67589), where discrimination was
indistinguishable from chance.

## Data sources

| Accession | Role | Platform |
| --- | --- | --- |
| GSE89403 | Discovery cohort, four timepoints | Illumina RNA sequencing |
| GSE67589 | Independent cohort, cure vs relapse | Affymetrix HG-U133 Plus 2.0 |
| GPL570 | Probe-to-symbol annotation | — |
