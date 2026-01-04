# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-25

### Added
- Initial release of TB Treatment Failure Prediction pipeline
- Complete ML pipeline for predicting treatment outcomes from baseline transcriptomics
- XGBoost model achieving AUC 0.794 in nested cross-validation
- SHAP analysis for feature interpretation
- Pathway enrichment analysis
- ROC curve generation
- Gene ID to symbol mapping
- Comprehensive documentation and manuscript
- GitHub Actions CI/CD workflows
- MIT License

### Features
- **Data Processing**: Automated GEO data download and preprocessing
- **Machine Learning**: Three models (Logistic Regression, Random Forest, XGBoost)
- **Cross-Validation**: Nested stratified 3-fold CV
- **Class Balancing**: Handles severe class imbalance (2.8% failures)
- **Interpretability**: SHAP values for all predictions
- **Visualization**: ROC curves, SHAP plots, dependence plots
- **Reproducibility**: Complete code, data, and documentation

### Performance
- **Best Model**: XGBoost
- **Mean AUC**: 0.794 (95% CI: 0.699-0.854)
- **Top Gene**: USP30 (ubiquitin-specific protease)
- **Clinical Utility**: 90% sensitivity → 60% specificity

### Documentation
- Complete README with installation and usage instructions
- Detailed methods documentation
- Manuscript draft for EBioMedicine
- Cover letter and supplementary materials
- Author contributions (CRediT format)

### Data
- **Source**: GEO accession GSE89403
- **Samples**: 254 baseline samples with treatment outcomes
- **Features**: 16,147 genes
- **Outcomes**: 247 cures, 7 failures

### Citation
```bibtex
@article{siddalingaiah2026treatment,
  title={Baseline Blood Transcriptomic Signatures Predict Treatment Failure in Tuberculosis: A Machine Learning Study},
  author={Siddalingaiah, H S},
  journal={EBioMedicine},
  year={2026},
  note={Submitted}
}
```

### Contributors
- Dr. Siddalingaiah H S (ORCID: 0000-0002-4771-8285)

---

## [Unreleased]

### Planned
- External validation in independent cohorts
- Integration with clinical risk factors
- Docker container for reproducibility
- Web application for predictions
- Additional pathway databases
- Mechanistic studies of top genes

---

## Version History

- **v1.0.0** (2025-12-25): Initial release
  - Complete ML pipeline
  - Manuscript submitted to EBioMedicine
  - All analysis code and documentation

---

## How to Cite

If you use this code or data, please cite:

**Siddalingaiah HS.** Baseline Blood Transcriptomic Signatures Predict Treatment Failure in Tuberculosis: A Machine Learning Study. *EBioMedicine* (submitted). 2026.

**Repository**: https://github.com/hssling/TB_Treatment_Failure_Prediction_by_Transcriptomics

**DOI**: [Zenodo DOI to be added]

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

**Dr. Siddalingaiah H S**  
Professor, Department of Community Medicine  
Shridevi Institute of Medical Sciences and Research Hospital  
Tumkur, Karnataka, India  
Email: hssling@yahoo.com  
ORCID: 0000-0002-4771-8285
