"""
Analysis: TB Diagnosis vs Non-TB Gene Expression
Question: Which genes are hyperactive at TB diagnosis and do they normalize after cure?
"""
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

print("="*80)
print("TB BIOMARKER ANALYSIS: Diagnosis vs Treatment Response")
print("="*80)

# Load data
print("\n1. Loading data...")
X = pd.read_parquet('outputs/dataset/feature_matrix.parquet')
meta = pd.read_parquet('outputs/dataset/metadata.parquet')
y = pd.read_parquet('outputs/dataset/labels.parquet')
cohorts = pd.read_parquet('outputs/metadata/cohorts.parquet')

print(f"   Feature matrix: {X.shape}")
print(f"   Metadata: {meta.shape}")
print(f"   Cohorts: {cohorts.shape}")

# Merge all data
print("\n2. Merging datasets...")
df = X.merge(y, on='sample_id').merge(meta, on='sample_id')
df_full = df.merge(cohorts[['sample_id', 'title', 'characteristics']], on='sample_id', how='left')

print(f"   Combined data: {df_full.shape}")

# Check available metadata
print("\n3. Available metadata columns:")
print(df_full.columns.tolist()[:15])

# Analyze cohorts
print("\n4. Cohort distribution:")
print(df_full['cohort_id'].value_counts())

# Check for timepoint information
print("\n5. Checking for timepoint/treatment information...")
if 'timepoint' in df_full.columns:
    print("   Timepoint column found:")
    print(df_full['timepoint'].value_counts())
else:
    print("   No 'timepoint' column in processed data")
    print("   Checking 'title' field for timepoint info...")
    if 'title' in df_full.columns:
        sample_titles = df_full['title'].head(10)
        print("\n   Sample titles (first 10):")
        for i, title in enumerate(sample_titles, 1):
            print(f"   {i}. {title}")

# Analyze GSE107991 (Active TB vs LTBI/Control)
print("\n" + "="*80)
print("ANALYSIS 1: Active TB vs Non-TB (GSE107991)")
print("="*80)

gse107991 = df_full[df_full['cohort_id'] == 'GSE107991'].copy()
print(f"\nGSE107991 samples: {len(gse107991)}")
print(f"Label distribution:")
print(f"  - Active TB (label=1): {(gse107991['label']==1).sum()}")
print(f"  - LTBI/Control (label=0): {(gse107991['label']==0).sum()}")

if len(gse107991) > 0:
    # Get gene columns
    gene_cols = [col for col in gse107991.columns if col.startswith('ENSG')]
    print(f"\nNumber of genes: {len(gene_cols)}")
    
    # Separate Active TB vs Non-TB
    active_tb = gse107991[gse107991['label'] == 1]
    non_tb = gse107991[gse107991['label'] == 0]
    
    print(f"\nActive TB samples: {len(active_tb)}")
    print(f"Non-TB samples: {len(non_tb)}")
    
    # Calculate differential expression
    print("\n6. Calculating differential expression...")
    results = []
    
    for gene in gene_cols[:100]:  # Test on first 100 genes for speed
        active_vals = active_tb[gene].values
        non_tb_vals = non_tb[gene].values
        
        # T-test
        t_stat, p_val = stats.ttest_ind(active_vals, non_tb_vals)
        
        # Fold change (log2)
        mean_active = np.mean(active_vals)
        mean_non_tb = np.mean(non_tb_vals)
        fold_change = mean_active - mean_non_tb  # Already log-transformed
        
        results.append({
            'gene': gene,
            'mean_active_tb': mean_active,
            'mean_non_tb': mean_non_tb,
            'fold_change': fold_change,
            't_statistic': t_stat,
            'p_value': p_val
        })
    
    results_df = pd.DataFrame(results)
    results_df['abs_fold_change'] = results_df['fold_change'].abs()
    results_df = results_df.sort_values('abs_fold_change', ascending=False)
    
    print("\nTop 20 differentially expressed genes (Active TB vs Non-TB):")
    print(results_df.head(20)[['gene', 'fold_change', 'p_value']].to_string(index=False))
    
    # Save results
    results_df.to_csv('outputs/interpretation/tb_vs_nontb_genes.csv', index=False)
    print("\n   Saved to: outputs/interpretation/tb_vs_nontb_genes.csv")

# Analyze GSE89403 (Treatment outcomes over time)
print("\n" + "="*80)
print("ANALYSIS 2: Treatment Response (GSE89403)")
print("="*80)

gse89403 = df_full[df_full['cohort_id'] == 'GSE89403'].copy()
print(f"\nGSE89403 samples: {len(gse89403)}")
print(f"Label distribution:")
print(f"  - Unfavorable outcome (label=1): {(gse89403['label']==1).sum()}")
print(f"  - Favorable outcome (label=0): {(gse89403['label']==0).sum()}")

# Check for timepoint information in titles
if 'title' in gse89403.columns:
    print("\n7. Analyzing sample titles for timepoint information...")
    sample_titles = gse89403['title'].head(20)
    print("\nSample titles (first 20):")
    for i, title in enumerate(sample_titles, 1):
        print(f"   {i}. {title}")
    
    # Extract timepoint from title
    print("\n8. Extracting timepoint information...")
    gse89403['timepoint_extracted'] = gse89403['title'].str.extract(r'(DX|day_\d+|week_\d+|month_\d+)', expand=False)
    
    if gse89403['timepoint_extracted'].notna().any():
        print("\nTimepoint distribution:")
        print(gse89403['timepoint_extracted'].value_counts())
        
        # Analyze diagnosis vs end-of-treatment
        dx_samples = gse89403[gse89403['timepoint_extracted'] == 'DX']
        week24_samples = gse89403[gse89403['timepoint_extracted'] == 'week_24']
        
        if len(dx_samples) > 0 and len(week24_samples) > 0:
            print(f"\nDiagnosis (DX) samples: {len(dx_samples)}")
            print(f"Week 24 samples: {len(week24_samples)}")
            
            # Only compare cured patients
            dx_cured = dx_samples[dx_samples['label'] == 0]
            week24_cured = week24_samples[week24_samples['label'] == 0]
            
            print(f"\nCured patients at diagnosis: {len(dx_cured)}")
            print(f"Cured patients at week 24: {len(week24_cured)}")
            
            if len(dx_cured) > 5 and len(week24_cured) > 5:
                print("\n9. Comparing gene expression: Diagnosis vs Post-treatment (Cured patients)")
                
                treatment_results = []
                for gene in gene_cols[:100]:
                    dx_vals = dx_cured[gene].values
                    week24_vals = week24_cured[gene].values
                    
                    t_stat, p_val = stats.ttest_ind(dx_vals, week24_vals)
                    
                    mean_dx = np.mean(dx_vals)
                    mean_week24 = np.mean(week24_vals)
                    fold_change = mean_dx - mean_week24
                    
                    treatment_results.append({
                        'gene': gene,
                        'mean_diagnosis': mean_dx,
                        'mean_post_treatment': mean_week24,
                        'fold_change': fold_change,
                        't_statistic': t_stat,
                        'p_value': p_val
                    })
                
                treatment_df = pd.DataFrame(treatment_results)
                treatment_df['abs_fold_change'] = treatment_df['fold_change'].abs()
                treatment_df = treatment_df.sort_values('abs_fold_change', ascending=False)
                
                print("\nTop 20 genes that change with treatment (Diagnosis vs Week 24):")
                print(treatment_df.head(20)[['gene', 'fold_change', 'p_value']].to_string(index=False))
                
                treatment_df.to_csv('outputs/interpretation/treatment_response_genes.csv', index=False)
                print("\n   Saved to: outputs/interpretation/treatment_response_genes.csv")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
