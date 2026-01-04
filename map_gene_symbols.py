
import pandas as pd
import requests
import time

print("=== Mapping Gene IDs to Symbols ===\n")

# Load top features
top_features = pd.read_csv("reports/tables/top_50_features_shap.csv")
print(f"Total features to map: {len(top_features)}")

# Extract Ensembl IDs
gene_ids = top_features['feature'].tolist()

# Use Ensembl REST API to map IDs to symbols
def get_gene_symbol(ensembl_id):
    """Query Ensembl REST API for gene symbol"""
    try:
        url = f"https://rest.ensembl.org/lookup/id/{ensembl_id}?content-type=application/json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('display_name', ensembl_id)
        else:
            return ensembl_id
    except:
        return ensembl_id

# Map gene IDs (with rate limiting)
gene_symbols = []
for i, gene_id in enumerate(gene_ids):
    symbol = get_gene_symbol(gene_id)
    gene_symbols.append(symbol)
    
    if (i + 1) % 10 == 0:
        print(f"Mapped {i + 1}/{len(gene_ids)} genes...")
        time.sleep(1)  # Rate limiting

# Add symbols to dataframe
top_features['gene_symbol'] = gene_symbols

# Save updated table
top_features.to_csv("reports/tables/top_50_features_with_symbols.csv", index=False)
print(f"\n✅ Saved: reports/tables/top_50_features_with_symbols.csv")

# Display top 20
print("\n=== Top 20 Genes with Symbols ===")
print(top_features[['feature', 'gene_symbol', 'mean_abs_shap']].head(20).to_string(index=False))

# Create a formatted table for manuscript
manuscript_table = top_features.head(10)[['feature', 'gene_symbol', 'mean_abs_shap']].copy()
manuscript_table.columns = ['Ensembl ID', 'Gene Symbol', 'Mean |SHAP|']
manuscript_table['Mean |SHAP|'] = manuscript_table['Mean |SHAP|'].round(3)
manuscript_table.index = range(1, 11)

print("\n=== Manuscript Table (Top 10) ===")
print(manuscript_table.to_markdown())

# Save for manuscript
manuscript_table.to_csv("reports/tables/manuscript_table2_top10genes.csv")
print("\n✅ Saved: reports/tables/manuscript_table2_top10genes.csv")
