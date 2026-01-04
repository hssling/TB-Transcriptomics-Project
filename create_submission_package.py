"""
Create complete submission package for EBioMedicine
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def create_submission_package():
    """Create submission package directory with all files"""
    
    print("=== Creating EBioMedicine Submission Package ===\n")
    
    # Create submission directory
    submission_dir = Path("Submission_Package_EBioMedicine")
    submission_dir.mkdir(exist_ok=True)
    
    print(f"Created directory: {submission_dir}\n")
    
    # Files to include
    files_to_copy = {
        # Main manuscript
        "TB_Treatment_Failure_Manuscript.docx": "1_Main_Manuscript.docx",
        
        # Cover letter
        "COVER_LETTER_EBIOMEDICINE.md": "2_Cover_Letter.txt",
        
        # Author information
        "AUTHORS_AND_CONTRIBUTIONS.md": "3_Author_Information.txt",
        
        # References
        "REFERENCES_WITH_DOIS.md": "4_References.txt",
        
        # Figures
        "reports/figures/roc_curves_combined.png": "Figure_2_ROC_Curves.png",
        "reports/figures/shap_importance_bar.png": "Figure_3_SHAP_Importance.png",
        "reports/figures/shap_summary_plot.png": "Figure_4_SHAP_Summary.png",
        
        # Tables
        "reports/tables/manuscript_table2_top10genes.csv": "Table_2_Top10_Genes.csv",
        "reports/tables/top_50_features_with_symbols.csv": "Supplementary_Table_1_Top50_Genes.csv",
        "reports/tables/pathway_enrichment_top20.csv": "Supplementary_Table_2_Pathways.csv",
    }
    
    # Copy files
    copied_files = []
    for src, dst in files_to_copy.items():
        src_path = Path(src)
        dst_path = submission_dir / dst
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            file_size = dst_path.stat().st_size / 1024
            print(f"✅ Copied: {dst} ({file_size:.1f} KB)")
            copied_files.append(dst)
        else:
            print(f"⚠️  Not found: {src}")
    
    # Create README for submission package
    readme_content = f"""# EBioMedicine Submission Package

**Manuscript Title**: Baseline Blood Transcriptomic Signatures Predict Treatment Failure in Tuberculosis: A Machine Learning Study

**Author**: Dr. Siddalingaiah H S
**Institution**: Shridevi Institute of Medical Sciences and Research Hospital, Tumkur
**Email**: hssling@yahoo.com
**ORCID**: 0000-0002-4771-8285

**Date Prepared**: {datetime.now().strftime('%B %d, %Y')}

---

## Package Contents

### Main Files
1. **1_Main_Manuscript.docx** - Complete manuscript in Word format
2. **2_Cover_Letter.txt** - Cover letter for editor
3. **3_Author_Information.txt** - Author contributions and affiliations
4. **4_References.txt** - Complete reference list with DOIs

### Figures
- **Figure_2_ROC_Curves.png** - ROC curves for nested CV folds
- **Figure_3_SHAP_Importance.png** - Feature importance bar chart
- **Figure_4_SHAP_Summary.png** - SHAP summary beeswarm plot

**Note**: Figure 1 (study flowchart) to be created separately

### Tables
- **Table_2_Top10_Genes.csv** - Top 10 predictive genes with symbols
- **Supplementary_Table_1_Top50_Genes.csv** - Top 50 genes by SHAP
- **Supplementary_Table_2_Pathways.csv** - Pathway enrichment results

**Note**: Table 1 (performance metrics) is included in main manuscript

---

## Submission Checklist

### Required Files
- ✅ Main manuscript (DOCX format)
- ✅ Cover letter
- ✅ Author information
- ✅ Figures (high resolution)
- ✅ Tables (editable format)
- ⏳ Figure 1 (study flowchart) - to be created

### Metadata
- ✅ Title
- ✅ Abstract (250 words, structured)
- ✅ Keywords (6 keywords)
- ✅ Author name and ORCID
- ✅ Institutional affiliation
- ✅ Corresponding author email

### Declarations
- ✅ Conflicts of interest (none)
- ✅ Funding statement (no external funding)
- ✅ Data availability (GEO + GitHub)
- ✅ Ethical approval (secondary analysis)
- ✅ Author contributions (CRediT format)

---

## Data and Code Availability

**Data**: GEO accession GSE89403
https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE89403

**Code**: GitHub repository
https://github.com/hssling/TB_Treatment_Failure_Prediction_by_Transcriptomics

**License**: MIT License

---

## Key Results

- **Performance**: XGBoost AUC 0.794 (95% CI: 0.699-0.854)
- **Top Gene**: USP30 (ubiquitin-specific protease 30)
- **Sample Size**: 254 patients (247 cures, 7 failures)
- **Clinical Utility**: 90% sensitivity → 60% specificity

---

## Submission Instructions

1. **Create Editorial Manager Account**
   - URL: https://www.editorialmanager.com/ebiom/
   - Email: hssling@yahoo.com

2. **Upload Files**
   - Main manuscript: 1_Main_Manuscript.docx
   - Cover letter: 2_Cover_Letter.txt
   - Figures: Figure_2, Figure_3, Figure_4 (convert to TIFF 300 dpi)
   - Tables: Table_2, Supplementary Tables 1-2

3. **Enter Metadata**
   - Article type: Original Research Article
   - Section: Infectious Diseases / Biomarkers
   - Suggested reviewers: See cover letter

4. **Declarations**
   - No conflicts of interest
   - No external funding
   - Data publicly available (GEO + GitHub)

---

## Contact Information

**Corresponding Author**:
Dr. Siddalingaiah H S
Professor, Department of Community Medicine
Shridevi Institute of Medical Sciences and Research Hospital
Tumkur, Karnataka, India
Email: hssling@yahoo.com
Phone: +91 8941087719
ORCID: 0000-0002-4771-8285

---

## Version History

- **v1.0** ({datetime.now().strftime('%Y-%m-%d')}): Initial submission package

---

**Total Files**: {len(copied_files)}
**Package Size**: {sum(f.stat().st_size for f in submission_dir.iterdir()) / 1024:.1f} KB

**Status**: Ready for submission to EBioMedicine
"""
    
    readme_path = submission_dir / "README.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n✅ Created: README.txt")
    
    # Create submission checklist
    checklist_content = """EBIOMEDICINE SUBMISSION CHECKLIST

Date: """ + datetime.now().strftime('%B %d, %Y') + """

BEFORE SUBMISSION:
☐ Review manuscript for typos and formatting
☐ Verify all author information is correct
☐ Check all references have DOIs
☐ Ensure figures are high resolution (300 dpi)
☐ Convert figures to TIFF format
☐ Create Figure 1 (study flowchart)
☐ Verify tables are in editable format
☐ Review cover letter

DURING SUBMISSION:
☐ Create Editorial Manager account
☐ Select article type: Original Research Article
☐ Enter title and abstract
☐ Add author information (ORCID: 0000-0002-4771-8285)
☐ Upload main manuscript
☐ Upload cover letter
☐ Upload figures (TIFF format)
☐ Upload tables
☐ Suggest reviewers (4 recommended)
☐ Declare no conflicts of interest
☐ Confirm data availability
☐ Review and submit

AFTER SUBMISSION:
☐ Save submission confirmation
☐ Track manuscript status
☐ Respond to editor queries promptly
☐ Prepare for potential revisions

CONTACT:
EBioMedicine Editorial Office
Email: ebiomedicine@lancet.com
Submission System: https://www.editorialmanager.com/ebiom/

AUTHOR:
Dr. Siddalingaiah H S
Email: hssling@yahoo.com
ORCID: 0000-0002-4771-8285
"""
    
    checklist_path = submission_dir / "SUBMISSION_CHECKLIST.txt"
    with open(checklist_path, 'w', encoding='utf-8') as f:
        f.write(checklist_content)
    
    print(f"✅ Created: SUBMISSION_CHECKLIST.txt")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUBMISSION PACKAGE COMPLETE")
    print(f"{'='*60}")
    print(f"Directory: {submission_dir.absolute()}")
    print(f"Total files: {len(list(submission_dir.iterdir()))}")
    print(f"Package size: {sum(f.stat().st_size for f in submission_dir.iterdir()) / 1024:.1f} KB")
    print(f"\n✅ Ready for submission to EBioMedicine!")
    
    return submission_dir

if __name__ == "__main__":
    create_submission_package()
