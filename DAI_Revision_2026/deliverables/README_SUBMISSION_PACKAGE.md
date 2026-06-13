# DAI Major Revision — Submission Package

**Manuscript:** *Baseline whole-blood transcriptomic risk stratification for unfavourable tuberculosis treatment outcome: an exploratory machine-learning and immune-deconvolution study*
**Submission ID:** 28df71d5-9f1a-4e4d-8cd3-8fcf4ef17dfb · **Journal:** Discover Artificial Intelligence · **Deadline:** 22 Jun 2026

## Files to upload
1. **TB_Treatment_Failure_DAI_MajorRevision_v13.docx** — revised manuscript; all revised/added content highlighted yellow (tracked-changes requirement). Includes the new **Declarations** section.
2. **Supplementary_Material_DAI_MajorRevision_v13.docx** — Tables S1–S11 + Supplementary Figures S1 (volcano), S2 (SHAP).
3. **Response_to_Reviewers_DAI_MajorRevision.docx** — point-by-point table (Editor, R1, R2, R3): comment → response → location.
4. **/figures** — Figures 1–4 + volcano + SHAP (300 dpi, enlarged fonts).

## What changed scientifically (honest reanalysis)
The original submission's headline (ROC-AUC 0.79) was inflated by **timepoint leakage** (same patient at multiple timepoints across train/test). Rebuilt on a **leakage-free baseline cohort** (GSE89403 pre-treatment/DX samples, one per subject: N=90, 7 failures, 83 cures):

| Metric | Original | Honest reanalysis |
|---|---|---|
| ROC-AUC | 0.79 | **0.67** (95% CI 0.38–0.89); LOO 0.64; **permutation p=0.11 (n.s.)** |
| Operating point | "high accuracy" | Sens 0.71 / Spec 0.73 / NPV 0.97 / PPV 0.19 (rule-out) |
| Neutrophil-high | p=3.2e-5 | p=0.057, rank-biserial r=−0.44 (borderline) |
| T-cell-low | p=1.1e-4 | n.s. at baseline (p=0.47) |
| DEG | "50 genes" | ~1,600 nominal, **0 survive FDR** |
| Y-linked predictors | "top predictors" | **sex-confound artifact** (not DE at baseline) |

**Robust findings retained:** ML↔deconvolution concordance (ρ=0.66/−0.66, p≈1e-10); neutrophil association sex-independent (OR≈4.5); neutrophil-signature genes neutrophil-specific in a granulocyte-containing reference (HPA, 10/12); external neutrophil↔T-cell anti-structure reproduced in GSE193979 (ρ=−0.41).

## Reviewer coverage (summary)
- **Causal language removed** (R2.8): Glasso = undirected conditional-dependency network; outcome not a node; new Figure 4.
- **Full metric suite + PR + confusion + calibration** (R2.2); class distribution in Methods (R2.1).
- **External validation**: documented exclusion table (R2.3) + label-free portability; GSE193979 outcomes not in GEO.
- **SHAP, DEG/volcano, enrichment** (R2.5); full feature list with symbols (R2.4).
- **PBMC3k replaced** by granulocyte-containing HPA atlas (R2.6).
- **Confounders** HIV/DR (cohort exclusion), bacterial load, sex (R2.9).
- **Baseline stratification foregrounded** (R1.9, R2.10); **WHO/clinical claims tempered** (R2.11).
- **Violins + rank-biserial effect sizes** (R2.12); benchmark vs literature incl. PMIDs 38357663/38380250/38514736 (R1.3, R3.1); DOTS/SMOTE defined; in-text figure refs; larger fonts.

## Reproducibility
Analysis scripts: `DAI_Revision_2026/analysis/00–11_*.py`. Result tables/JSON: `DAI_Revision_2026/tables/`. An independent recheck (`09_recheck.py`) verified data integrity, AUC across three CV procedures, a permutation null, and effect-size bootstrap CIs.

## Honesty note
With 7 events the baseline predictor is **not statistically significant** (permutation p=0.11); the paper is framed as exploratory/hypothesis-generating and explicitly **not clinically actionable**, consistent with the approved "full reframe, no overclaiming" direction and the field-wide difficulty of baseline failure prediction (RePORT-Brazil AUC<0.70).
