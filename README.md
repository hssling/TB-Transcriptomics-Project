# TB Transcriptomics Project: Rapid Normalization Kinetics

**Principal Investigator**: Dr Siddalingaiah H S  
**Affiliation**: Shridevi Institute of Medical Sciences and Research Hospital, Tumkur  
**Contact**: hssling@yahoo.com | 8941087719  
**ORCID**: [0000-0002-4771-8285](https://orcid.org/0000-0002-4771-8285)

## Overview
This repository contains the code and data analysis pipeline for the study **"Dynamic Transcriptomic Signatures in Tuberculosis: Validating Rapid Normalization Kinetics"**.

We demonstrate that host gene expression profiles, specifically Inflammatory (Hyperactive) and T-cell Homeostatic (Suppressed) modules, normalize significantly within **7 days** of successful treatment initiation.

## Repository Structure
*   `src/`: Python scripts for differential expression and longitudinal analysis.
*   `results/`: Generated high-resolution figures and tables.
*   `manuscript/`: Final manuscript versions.

## Reproduction
To reproduce the findings:
1.  Install dependencies: `pip install pandas scipy seaborn matplotlib`
2.  Run analysis: `python src/analysis_core.py`
3.  Generate plots: `python src/visualization.py`

## Citation
If you use this code, please cite:
> Siddalingaiah H S et al. (2025). Rapid Transcriptomic Normalization in Tuberculosis. *Clinical Infectious Diseases* (Submitted).
