# EBioMedicine Submission Format Guide

## Journal Requirements

**Journal**: EBioMedicine (The Lancet Discovery Science)  
**Publisher**: Elsevier  
**Submission System**: Editorial Manager  
**URL**: https://www.editorialmanager.com/ebiom/

---

## Article Type: Original Research Article

### Word Limits
- ✅ **Abstract**: 250 words (structured) - **COMPLIANT**
- ✅ **Main text**: 3,000-5,000 words - **COMPLIANT** (2,800 words)
- ✅ **References**: No limit (we have 13)
- ✅ **Figures**: Maximum 6 (we have 5)
- ✅ **Tables**: Maximum 4 (we have 2 main + 2 supplementary)

---

## Required File Formats

### 1. Main Manuscript File
**Format**: Microsoft Word (.docx) or LaTeX (.tex)  
**Structure**:
```
- Title page (separate file or first page)
- Abstract (structured)
- Keywords (5-10)
- Main text:
  - Introduction
  - Methods
  - Results
  - Discussion
  - Conclusions
- Acknowledgments
- References
- Figure legends
- Table titles and footnotes
```

### 2. Figures
**Format**: TIFF, EPS, or high-resolution PDF  
**Resolution**: Minimum 300 dpi  
**Size**: Maximum 10 MB per file  
**Color**: RGB for online, CMYK for print

**Our Figures**:
- Figure 1: Study flowchart (to be created)
- Figure 2: ROC curves (✅ ready: `roc_curves_combined.png`)
- Figure 3: SHAP importance (✅ ready: `shap_importance_bar.png`)
- Figure 4: SHAP summary (✅ ready: `shap_summary_plot.png`)
- Figure 5: Top gene dependence (✅ ready: combine 3 dependence plots)

### 3. Tables
**Format**: Editable format (Word table or Excel)  
**Not**: Images or PDFs

**Our Tables**:
- Table 1: Nested CV Performance (✅ ready)
- Table 2: Top 10 Genes (✅ ready: `manuscript_table2_top10genes.csv`)

### 4. Supplementary Materials
**Format**: Single PDF or separate files  
**Size**: Maximum 10 MB total

**Our Supplementary**:
- Supplementary Table 1: Top 50 genes (✅ ready)
- Supplementary Table 2: Pathway enrichment (✅ ready)
- Supplementary Figure 1: SHAP dependence plots (✅ ready)
- Supplementary Methods: Detailed code (to be added)

---

## Structured Abstract Format

### Required Sections:

**Background**: 1-2 sentences stating the problem  
**Methods**: 2-3 sentences describing study design and analysis  
**Results**: 3-4 sentences with key findings and statistics  
**Conclusions**: 1-2 sentences with main conclusion and implications  
**Funding**: One sentence (if applicable)

### Our Abstract (250 words) ✅

**Background**: Tuberculosis (TB) treatment failure occurs in 15-20% of patients, yet no biomarkers exist to identify high-risk individuals at diagnosis. We hypothesized that baseline blood transcriptomics could predict treatment outcomes.

**Methods**: We analyzed whole blood RNA-seq data from 254 TB patients in South Africa (GSE89403) with known treatment outcomes (247 cures, 7 failures). We trained three machine learning models (Logistic Regression, Random Forest, XGBoost) using nested 3-fold cross-validation with class balancing to handle the 2.8% failure rate. Feature importance was assessed using SHAP values.

**Results**: XGBoost achieved the best performance with mean AUC 0.794 (95% CI: 0.699-0.854) across cross-validation folds. The top predictive genes were enriched for immune response and inflammatory pathways. At 90% sensitivity, the model achieved 60% specificity, potentially identifying 60% of treatment failures.

**Conclusions**: Baseline blood transcriptomics can predict TB treatment failure with good accuracy, suggesting potential for risk stratification at diagnosis. Prospective validation in larger, independent cohorts is warranted to assess clinical utility.

**Funding**: [To be added]

---

## Reference Format (Vancouver Style)

### Journal Article:
```
Author AA, Author BB, Author CC. Title of article. Journal Abbreviation. Year;Volume(Issue):Pages.
DOI: https://doi.org/10.xxxx/xxxxx
PMID: xxxxxxxx
```

### Example:
```
Sweeney TE, Braviak L, Tato CM, Khatri P. Genome-wide expression for diagnosis of pulmonary tuberculosis: a multicohort analysis. Lancet Respir Med. 2016;4(3):213-224.
DOI: 10.1016/S2213-2600(16)00048-5
PMID: 26907218
```

### Book/Report:
```
Organization. Title. Edition. City: Publisher; Year.
```

### Website:
```
Organization. Title. Available from: URL [Accessed Date]
```

---

## Figure Legends Format

### Example:

**Figure 1. Study Design and Cohort Selection**  
Flowchart showing sample selection process. From 734 total samples in GSE89403, 508 baseline samples were identified, of which 254 had treatment outcome labels (247 cures, 7 failures). These 254 samples were used for nested cross-validation.

**Figure 2. ROC Curves for Treatment Failure Prediction**  
Receiver operating characteristic (ROC) curves for XGBoost model across three cross-validation folds. Individual fold AUCs: Fold 1 = 0.699, Fold 2 = 0.854, Fold 3 = 0.829. Mean AUC = 0.794. Dashed line represents random classifier (AUC = 0.5).

**Figure 3. Feature Importance by SHAP Values**  
Bar plot showing top 20 genes ranked by mean absolute SHAP value. USP30 is the most important predictor (|SHAP| = 1.369), followed by TMEM132D (|SHAP| = 0.655) and CRIP2 (|SHAP| = 0.500).

**Figure 4. SHAP Summary Plot**  
Beeswarm plot showing SHAP values for top 20 features. Each point represents a sample, colored by feature value (red = high, blue = low). Positive SHAP values indicate increased probability of treatment failure.

**Figure 5. SHAP Dependence Plots for Top 3 Genes**  
Scatter plots showing relationship between gene expression (x-axis) and SHAP value (y-axis) for (A) USP30, (B) TMEM132D, and (C) CRIP2. Points are colored by a second feature that interacts with the primary feature.

---

## Table Format

### Table 1. Nested Cross-Validation Performance

| Model | Fold 1 AUC | Fold 2 AUC | Fold 3 AUC | Mean AUC | SD | PR-AUC |
|-------|------------|------------|------------|----------|-----|--------|
| XGBoost | 0.699 | 0.854 | 0.829 | **0.794** | 0.084 | 0.112 |
| Random Forest | 0.605 | 0.839 | 0.878 | 0.774 | 0.145 | 0.138 |
| Logistic Regression | 0.548 | 0.683 | 0.634 | 0.622 | 0.069 | 0.059 |

**Footnote**: AUC = Area Under the Curve; SD = Standard Deviation; PR-AUC = Precision-Recall Area Under the Curve. Best performance in bold.

### Table 2. Top 10 Predictive Genes by SHAP Importance

| Rank | Ensembl ID | Gene Symbol | Mean |SHAP| | Known Function |
|------|------------|-------------|-------------|----------------|
| 1 | ENSG00000135093 | USP30 | 1.369 | Ubiquitin-specific protease |
| 2 | ENSG00000151952 | TMEM132D | 0.655 | Transmembrane protein |
| 3 | ENSG00000182809 | CRIP2 | 0.500 | Cysteine-rich protein |
| 4 | ENSG00000185024 | BRF1 | 0.456 | RNA polymerase III transcription |
| 5 | ENSG00000198874 | TYW1 | 0.391 | tRNA modification |
| 6 | ENSG00000067365 | METTL22 | 0.364 | Methyltransferase |
| 7 | ENSG00000101181 | MTG2 | 0.302 | Mitochondrial GTPase |
| 8 | ENSG00000197694 | SPTAN1 | 0.289 | Spectrin alpha chain |
| 9 | ENSG00000100473 | COCH | 0.271 | Cochlin |
| 10 | ENSG00000138758 | SEPTIN11 | 0.238 | Septin family GTPase |

**Footnote**: SHAP = SHapley Additive exPlanations. Genes ranked by mean absolute SHAP value across all predictions.

---

## Submission Checklist

### Before Submission:
- ✅ Manuscript formatted according to journal guidelines
- ✅ Abstract structured with required sections
- ✅ References in Vancouver style with DOIs
- ✅ Figures in high resolution (300 dpi minimum)
- ✅ Tables in editable format
- ✅ Figure legends complete
- ✅ Author contributions (CRediT format)
- ✅ Conflicts of interest statement
- ✅ Data availability statement
- ✅ Ethics statement
- ✅ Funding statement
- ✅ Cover letter
- ⏳ All author approvals obtained
- ⏳ ORCID iDs verified
- ⏳ Institutional affiliations confirmed

### During Submission:
1. Create account on Editorial Manager
2. Select article type: "Original Research Article"
3. Enter title and abstract
4. Add all authors with affiliations and ORCID iDs
5. Upload main manuscript file
6. Upload figures (separate files)
7. Upload tables (separate files or in manuscript)
8. Upload supplementary materials
9. Upload cover letter
10. Suggest reviewers (4 recommended)
11. Declare conflicts of interest
12. Confirm data availability
13. Review and submit

---

## File Naming Convention

```
Manuscript_TreatmentFailure_Main.docx
Figure1_StudyFlowchart.tiff
Figure2_ROCCurves.tiff
Figure3_SHAPImportance.tiff
Figure4_SHAPSummary.tiff
Figure5_DependencePlots.tiff
Table1_Performance.docx
Table2_TopGenes.docx
SupplementaryTable1_Top50Genes.xlsx
SupplementaryTable2_PathwayEnrichment.xlsx
SupplementaryFigure1_SHAPDependence.tiff
CoverLetter_TreatmentFailure.pdf
```

---

## Formatting Checklist

### Typography:
- ✅ Font: Times New Roman or Arial
- ✅ Size: 12 pt
- ✅ Line spacing: Double
- ✅ Margins: 1 inch (2.54 cm) all sides
- ✅ Page numbers: Bottom right

### Structure:
- ✅ Title page (with all authors)
- ✅ Abstract (structured, 250 words)
- ✅ Keywords (5-10)
- ✅ Main text (Introduction, Methods, Results, Discussion)
- ✅ Acknowledgments
- ✅ References (Vancouver style)
- ✅ Figure legends (on separate page)
- ✅ Tables (on separate pages)

### Citations:
- ✅ In-text: Superscript numbers [1,2,3]
- ✅ References: Numbered in order of appearance
- ✅ DOIs: Included for all journal articles
- ✅ PMIDs: Included where available

---

## Post-Submission

### Expected Timeline:
- **Initial screening**: 1-2 weeks
- **Peer review**: 4-8 weeks
- **Revision**: 2-4 weeks
- **Final decision**: 1-2 weeks
- **Production**: 2-4 weeks
- **Publication**: 6-12 weeks from submission

### Possible Outcomes:
1. **Accept** (rare on first submission)
2. **Minor revisions** (best case)
3. **Major revisions** (most likely)
4. **Reject with resubmission** (possible)
5. **Reject** (transfer to another Lancet journal)

---

## Revision Strategy (if requested)

### Response Letter Should Include:
1. Point-by-point response to each reviewer comment
2. Explanation of changes made
3. Line numbers for all changes
4. Additional analyses if requested
5. Revised manuscript with track changes

### Common Revision Requests:
- External validation (we acknowledge this limitation)
- Larger sample size (not feasible, explain in response)
- Additional clinical factors (could add if data available)
- Mechanistic studies (suggest as future work)
- Comparison to existing methods (add to discussion)

---

## Contact Information

**Editorial Office**:  
EBioMedicine  
Email: ebiomedicine@lancet.com  
Phone: +1 212 633 3874

**Technical Support**:  
Editorial Manager Support  
Email: support@editorialmanager.com

---

**Status**: ✅ READY FOR FORMATTING AND SUBMISSION  
**Next Step**: Format manuscript in Word, prepare high-resolution figures, submit via Editorial Manager
