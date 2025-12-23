
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set style
sns.set(context='paper', style='white')

def main():
    # 1. Load Data
    cohorts = pd.read_parquet('outputs/metadata/cohorts.parquet')
    gse89403 = cohorts[cohorts['cohort_id'] == 'GSE89403'].copy()
    gse89403['patient_id'] = gse89403['title'].str.extract(r'(S\d+)_', expand=False)
    
    # Filter Cured Paired
    # We need patients who have ALL 3 timepoints for the heatmap ideally, or at least Baseline/Month6
    # Let's pivot to check coverage
    
    X = pd.read_parquet('outputs/dataset/feature_matrix.parquet')
    
    # Merge
    merged = gse89403.merge(X, on='sample_id')
    
    # 2. Select Genes of Interest (Top 10 UP, Top 10 DOWN from Diagnosis)
    # Based on previous analysis (ENSG...2549 etc)
    # I'll manually define the list based on "High Variance" in the dataset if I don't have the p-value list loaded
    # Or better: Sort by Fold Change Baseline vs Month 6 to find the most responsive ones.
    
    # Calculate Mean Baseline vs Month 6 for all genes
    baseline = merged[merged['timepoint'] == 'baseline']
    month6 = merged[merged['timepoint'] == 'month6']
    
    # Calculate simple means
    mean_b = baseline.select_dtypes(include=np.number).mean()
    mean_m6 = month6.select_dtypes(include=np.number).mean()
    
    # Calculate Delta (Baseline - Month 6)
    # Positive Delta = Decreased (Hyperactive normalized)
    # Negative Delta = Increased (Suppressed recovered)
    delta = mean_b - mean_m6
    
    top_up = delta.sort_values(ascending=False).head(10).index.tolist()
    top_down = delta.sort_values(ascending=True).head(10).index.tolist()
    
    selected_genes = top_up + top_down
    
    # 3. Create Heatmap Data
    # Group by Timepoint
    heatmap_data = merged.groupby('timepoint')[selected_genes].mean()
    # Reorder timepoints
    heatmap_data = heatmap_data.reindex(['baseline', 'week1', 'month6'])
    
    # Z-score normalize by gene (column) for visualization
    heatmap_norm = (heatmap_data - heatmap_data.mean()) / heatmap_data.std()
    
    # Transpose for Gene x Time
    heatmap_plot = heatmap_norm.T
    
    # Plot
    plt.figure(figsize=(8, 10))
    # Add a separation line between UP and DOWN
    sns.heatmap(heatmap_plot, cmap='RdBu_r', center=0, annot=False, cbar_kws={'label': 'Z-Score Expression'})
    plt.title('longitudinal Trajectory of Top 20 Biomarkers', fontsize=14, fontweight='bold')
    plt.xlabel('Treatment Phase', fontweight='bold')
    plt.ylabel('Biomarker Genes', fontweight='bold')
    plt.tight_layout()
    plt.savefig('reports/figures/innovative_heatmap.png', dpi=300)
    print("Heatmap saved: reports/figures/innovative_heatmap.png")
    
    # 4. Generate Table Data (Kinetics)
    # We need a table of actual values and p-values for these genes
    
    print("\n--- GENERATING KINETICS TABLE DATA ---")
    results = []
    
    # Get paired week 1 and month 6
    pivot = merged.pivot_table(index='patient_id', columns='timepoint', values=selected_genes)
    
    for gene in selected_genes:
        # Get sub-dataframe (columns: baseline, week1, month6)
        sub_df = pivot[gene]
        
        # Baseline-Week1
        bw1 = sub_df.dropna(subset=['baseline', 'week1'])
        if len(bw1) > 2:
            t1, p1 = stats.ttest_rel(bw1['baseline'], bw1['week1'])
            fc1 = np.mean(bw1['week1']) - np.mean(bw1['baseline'])
        else:
            p1, fc1 = 1.0, 0.0
            
        # Baseline-Month6
        bm6 = sub_df.dropna(subset=['baseline', 'month6'])
        if len(bm6) > 2:
            t6, p6 = stats.ttest_rel(bm6['baseline'], bm6['month6'])
            fc6 = np.mean(bm6['month6']) - np.mean(bm6['baseline'])
        else:
            p6, fc6 = 1.0, 0.0
            
        direction = "Hyperactive" if gene in top_up else "Suppressed"
        
        results.append({
            'Gene': gene,
            'Type': direction,
            'Week1_Change': f"{fc1:.2f}",
            'Week1_P': f"{p1:.1e}",
            'Month6_Change': f"{fc6:.2f}",
            'Month6_P': f"{p6:.1e}"
        })
        
    df_results = pd.DataFrame(results)
    df_results.to_csv('outputs/interpretation/kinetics_table.csv', index=False)
    print("Kinetics Table saved: outputs/interpretation/kinetics_table.csv")

if __name__ == "__main__":
    main()
