"""Pathway enrichment on baseline DEG nominal hits (R2.5). Exploratory, since
no gene survives FDR; uses Enrichr over-representation on top nominal DEGs."""
import warnings
import pandas as pd
warnings.filterwarnings("ignore")
import common
T = f"{common.ROOT}/DAI_Revision_2026/tables"

deg = pd.read_csv(f"{T}/wpB_DEG_corrected.csv")
top = deg[deg.p_value < 0.01].dropna(subset=["gene_symbol"])
genes = [g for g in top["gene_symbol"].unique() if isinstance(g, str) and g][:250]
print(f"Top nominal DEGs (p<0.01) for enrichment: {len(genes)}")

try:
    import gseapy as gp
    enr = gp.enrichr(gene_list=genes,
                     gene_sets=["GO_Biological_Process_2021", "KEGG_2021_Human",
                                "MSigDB_Hallmark_2020"],
                     organism="human", outdir=None)
    res = enr.results.sort_values("Adjusted P-value").head(25)
    res = res[["Gene_set", "Term", "Overlap", "P-value", "Adjusted P-value", "Genes"]]
    res.to_csv(f"{T}/wpB_enrichment.csv", index=False)
    print(res[["Gene_set", "Term", "Adjusted P-value"]].head(15).to_string(index=False))
    print("\nSaved wpB_enrichment.csv")
except Exception as e:
    print("Enrichr failed (offline?):", str(e)[:120])
    print("Falling back to existing reports/tables enrichment outputs.")
