import scanpy as sc
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# Setup paths
BASE_DIR = Path("D:/research-automation/TB multiomics/TB-Treatment-Failure-Clean")
FIG_DIR = BASE_DIR / "outputs/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

def run_tb_single_cell_validation():
    print("Step 1: Loading Human PBMC Reference Data...")
    try:
        adata = sc.datasets.pbmc3k()
    except Exception as e:
        print(f"Failed to download pbmc3k: {e}")
        return

    # Basic QC
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    
    # Normalization
    print("Step 2: Preprocessing and Clustering...")
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)
    
    # PCA & UMAP
    sc.pp.pca(adata, svd_solver='arpack')
    sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
    sc.tl.umap(adata)
    sc.tl.leiden(adata)
    
    # Calculate scores to assign types roughly based on markers
    # We will use the clusters as cell types for visualization
    sc.tl.rank_genes_groups(adata, 'leiden', method='t-test')
    
    # Treatment Failure Signature
    # Top 10 Genes from Manuscript
    failure_genes = [
        'USP30', 'TMEM132D', 'CRIP2', 'BRF1', 'TYW1',
        'METTL22', 'MTG2', 'SPTAN1', 'COCH', 'SEPTIN11'
    ]
    
    # Reference Markers to orient the DotPlot
    # B: MS4A1, T: CD3D, NK: GNLY, Mono: CD14, DC: FCER1A, Platelet: PPBP
    context_genes = ['MS4A1', 'CD3D', 'GNLY', 'CD14', 'FCER1A', 'PPBP']
    
    # Filter for available genes
    available_failure_genes = [g for g in failure_genes if g in adata.var_names]
    available_context_genes = [g for g in context_genes if g in adata.var_names]
    
    print(f"Mapping Failure Signature genes: {available_failure_genes}")
    print(f"Missing genes: {set(failure_genes) - set(available_failure_genes)}")
    
    # Plotting
    print("Step 3: Generating Validation Plots...")
    
    # 1. UMAP with top 3 predictive genes
    # USP30 is rank 1
    top_3 = available_failure_genes[:3]
    if top_3:
        sc.pl.umap(adata, color=top_3, frameon=False, show=False)
        plt.savefig(FIG_DIR / "sc_umap_failure_genes.png", bbox_inches='tight')
        plt.close()
    
    # 2. DotPlot: Context vs Failure Genes
    plot_genes = available_context_genes + available_failure_genes
    
    # Use Leiden clusters as the grouping
    dp = sc.pl.dotplot(adata, plot_genes, groupby='leiden', show=False)
    plt.savefig(FIG_DIR / "sc_dotplot_tb_failure.png", bbox_inches='tight')
    plt.close()
    
    # 3. Violin Plot for Top Gene USP30
    if 'USP30' in adata.var_names:
        sc.pl.violin(adata, ['USP30'], groupby='leiden', show=False)
        plt.savefig(FIG_DIR / "sc_violin_USP30.png", bbox_inches='tight')
        plt.close()

    # Move scanpy figures if saved elsewhere
    try:
        for f in Path("figures").glob("*.png"):
            f.rename(FIG_DIR / f.name)
        Path("figures").rmdir()
    except:
        pass

    print("✓ TB Single-cell validation complete. Figures generated.")

if __name__ == "__main__":
    run_tb_single_cell_validation()
