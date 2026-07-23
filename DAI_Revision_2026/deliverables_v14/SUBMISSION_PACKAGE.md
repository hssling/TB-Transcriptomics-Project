# Submission package

Manuscript: *Whole-blood transcriptomic signatures of unfavourable tuberculosis treatment outcome before and during therapy: an exploratory machine-learning and immune-deconvolution study*

## Files

| File | Contents |
| --- | --- |
| `TB_Treatment_Outcome_DAI_Revision_v14.docx` | Revised manuscript |
| `Response_to_Reviewers_DAI_Revision_v14.docx` | Point-by-point response, in table form |
| `Cover_Letter_DAI_Revision_v14.docx` | Cover letter |
| `Supplementary_Material_DAI_Revision_v14.docx` | Supplementary tables S1–S14 and figure S1 |
| `figures/` | Main figures at 300 dpi |
| `tables/` | Machine-readable result tables |

## Headline results

| Arm | n | Events | ROC-AUC (95% CI) | PR-AUC | Permutation p | Genes at FDR < 0.05 |
| --- | --- | --- | --- | --- | --- | --- |
| Pre-treatment | 90 | 7 | 0.65 (0.34–0.89) | 0.18 | 0.182 | 0 |
| Day 7 | 91 | 6 | 0.69 (0.56–0.82) | 0.11 | 0.202 | 0 |
| Week 4 | 92 | 8 | 0.60 (0.33–0.85) | 0.21 | 0.263 | 0 |
| Week 24 | 94 | 7 | 0.93 (0.81–1.00) | 0.67 | 0.006 | 5,924 |

Independent cohort (GSE67589): signature transfer ROC-AUC 0.31–0.53, every confidence interval spanning 0.5. The signature did not generalise, and the manuscript reports this as a negative result.

## Reproducing the analysis

```
python analysis/20_build_full_dataset.py     # rebuild from the GEO deposit
python analysis/21_arm_models.py             # discrimination per arm
python analysis/22_deconvolution_arms.py     # immune composition
python analysis/23_shap_arms.py              # feature attribution
python analysis/24_deg_arms.py               # differential expression
python analysis/25_enrichment.py             # pathway over-representation
python analysis/26_network_shap.py           # conditional-dependency network
python analysis/27_external_gse67589.py      # independent cohort
python analysis/28_flowchart.py              # study flow diagram
python analysis/29_comparative.py            # performance and contrast figures
python analysis/30_confounders.py            # sex and bacterial-load audit
```

Raw data are downloaded from the NCBI Gene Expression Omnibus on first run. Random seeds are fixed throughout.
