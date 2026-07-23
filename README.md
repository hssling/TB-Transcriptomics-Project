# TB Transcriptomics Project

**Principal Investigator**: Dr Siddalingaiah H S
**Affiliation**: Shridevi Institute of Medical Sciences and Research Hospital, Tumkur
**Contact**: hssling@yahoo.com
**ORCID**: [0000-0002-4771-8285](https://orcid.org/0000-0002-4771-8285)

This repository holds the analysis code for two related studies of host blood
transcriptomics in pulmonary tuberculosis. They share a codebase and some data,
but they ask different questions and are described separately below.

---

## Study 1 — Treatment outcome before and during therapy (current)

> **Whole-blood transcriptomic signatures of unfavourable tuberculosis treatment
> outcome before and during therapy: an exploratory machine-learning and
> immune-deconvolution study**
> Under review, *Discover Artificial Intelligence*.

**Branch: [`dai-revision-v14`](../../tree/dai-revision-v14) — this is the code
and data release accompanying that manuscript.** Everything for it lives under
`DAI_Revision_2026/`, and the reproduction guide is
[`DAI_Revision_2026/REPRODUCE_v14.md`](../../blob/dai-revision-v14/DAI_Revision_2026/REPRODUCE_v14.md).

### What the study asks

Whether whole blood carries information about eventual treatment outcome, and
at which point in the treatment course it becomes readable. Samples taken
before and during therapy describe two distinct biological states, so pooling
them conflates the question. Each timepoint of GSE89403 is therefore analysed
as a separate arm under one identical protocol, and the arms are then compared.

### What it finds

| Arm | n | Events | ROC-AUC (95% CI) | Permutation p | Genes at FDR < 0.05 |
| --- | --- | --- | --- | --- | --- |
| Pre-treatment | 90 | 7 | 0.65 (0.34–0.89) | 0.182 | 0 |
| Day 7 | 91 | 6 | 0.69 (0.56–0.82) | 0.202 | 0 |
| Week 4 | 92 | 8 | 0.60 (0.33–0.85) | 0.263 | 0 |
| Week 24 | 94 | 7 | 0.93 (0.81–1.00) | 0.006 | 5,924 |
| All timepoints | 367 | 28 | 0.68 (0.57–0.79) | 0.004 | — |

Outcome is not readable before treatment or through its first four weeks, and
is clearly readable at the end of therapy — where it is concurrent with outcome
ascertainment, and so is a marker of unresolved disease rather than a forecast.

Two negative results are reported with equal weight. Published signatures of
active tuberculosis, applied without fitting any parameter, matched or exceeded
the fitted models in **every** arm, so the machine learning added no predictive
value. And the signature did not transfer to an independent cohort (GSE67589),
where discrimination was indistinguishable from chance.

### Contents of the release

| Path | Contents |
| --- | --- |
| `DAI_Revision_2026/analysis/` | Numbered analysis scripts, in dependency order |
| `DAI_Revision_2026/tables2/` | Every numeric result, as CSV and JSON |
| `DAI_Revision_2026/figures2/` | Figures at 300 dpi |
| `DAI_Revision_2026/data2/` | Processed expression matrix, sample table, gene map |
| `DAI_Revision_2026/models/` | Frozen model per arm, selected features, SHA-256 manifest |
| `DAI_Revision_2026/deliverables_v14/` | Manuscript, supplementary material, response to reviewers |

Raw GEO data are not committed — they belong to the original depositors, and
the scripts fetch and cache them on first run (about 50 MB in total, from
GSE89403, GSE67589 and platform GPL570). `REPRODUCE_v14.md` lists each file,
its size, and which script retrieves it, and explains how to supply them
manually if the environment has no outbound network access.

### Reproducing it

```
pip install -r DAI_Revision_2026/requirements.txt
python DAI_Revision_2026/analysis/20_build_full_dataset.py   # downloads from GEO, builds the matrix
...                       # see REPRODUCE_v14.md for the full ordered list
```

From a clean checkout the first script reproduces the committed `data2/` byte
for byte: 16,145 genes, 367 libraries, 98 subjects. If those numbers differ,
something upstream has changed and the rest of the pipeline should not be
trusted.

Random seeds are fixed throughout, and the manuscript is rebuilt from the
analysis outputs by the `build_*_v14.py` scripts, so no reported number is
typed by hand.

**A note on the frozen models.** `.joblib` files are Python pickles and execute
code when loaded. Verify the SHA-256 in `DAI_Revision_2026/models/MANIFEST.json`
before loading these, or any other pickle you did not create yourself.

---

## Study 2 — Rapid normalization kinetics (earlier work)

> **Dynamic Transcriptomic Signatures in Tuberculosis: Validating Rapid
> Normalization Kinetics**

This study demonstrates that host gene expression profiles — specifically
inflammatory (hyperactive) and T-cell homeostatic (suppressed) modules —
normalize significantly within **7 days** of successful treatment initiation.

### Repository structure

* `src/` — Python scripts for differential expression and longitudinal analysis
* `results/` — Generated high-resolution figures and tables
* `manuscript/` — Final manuscript versions

### Reproduction

1. Install dependencies: `pip install -r requirements.txt`
2. **Option A: Quick analysis (manuscript figures)**
   * Run analysis: `python src/analysis_core.py`
   * Generate plots: `python src/visualization.py`
3. **Option B: Full machine-learning pipeline (reproduce model and validation)**
   * Run end-to-end: `python run_pipeline.py`
   * *Note: this downloads data, trains nested cross-validated models, and runs
     external validation.*

### Citation

> Siddalingaiah H S et al. (2025). Rapid Transcriptomic Normalization in
> Tuberculosis. *Clinical Infectious Diseases* (Submitted).

---

## Data sources

| Accession | Role | Platform |
| --- | --- | --- |
| GSE89403 | Treatment-response discovery cohort, four timepoints | Illumina RNA sequencing |
| GSE67589 | Independent outcome cohort, cure vs relapse | Affymetrix HG-U133 Plus 2.0 |
| GPL570 | Probe-to-symbol annotation | — |

## Licence

See [`LICENSE`](LICENSE).
