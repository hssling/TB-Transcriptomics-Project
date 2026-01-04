
import pandas as pd
import requests
import json
import time

print("=== Pathway Enrichment Analysis ===\n")

# Load top genes with symbols
top_genes = pd.read_csv("reports/tables/top_50_features_with_symbols.csv")
gene_symbols = top_genes['gene_symbol'].tolist()

print(f"Total genes for enrichment: {len(gene_symbols)}")
print(f"Gene list: {', '.join(gene_symbols[:20])}...")

# Enrichr API
ENRICHR_URL = 'https://maayanlab.cloud/Enrichr/addList'
ENRICHR_QUERY_URL = 'https://maayanlab.cloud/Enrichr/enrich'

# Gene libraries to query
libraries = [
    'KEGG_2021_Human',
    'GO_Biological_Process_2023',
    'Reactome_2022',
    'WikiPathway_2023_Human',
    'MSigDB_Hallmark_2020'
]

# Submit gene list to Enrichr
print("\n=== Submitting gene list to Enrichr ===")
genes_str = '\n'.join(gene_symbols)
payload = {
    'list': (None, genes_str),
    'description': (None, 'TB Treatment Failure Top 50 Genes')
}

try:
    response = requests.post(ENRICHR_URL, files=payload)
    if response.status_code != 200:
        raise Exception(f'Error analyzing gene list: {response.status_code}')
    
    data = response.json()
    user_list_id = data['userListId']
    print(f"✅ Gene list submitted. List ID: {user_list_id}")
    
    # Query each library
    all_results = {}
    
    for library in libraries:
        print(f"\nQuerying {library}...")
        time.sleep(1)  # Rate limiting
        
        query_string = f'?userListId={user_list_id}&backgroundType={library}'
        response = requests.get(ENRICHR_QUERY_URL + query_string)
        
        if response.status_code != 200:
            print(f"  ⚠️ Error querying {library}")
            continue
        
        data = response.json()
        
        if library in data and len(data[library]) > 0:
            # Parse results
            results = []
            for term in data[library][:10]:  # Top 10 terms
                results.append({
                    'Term': term[1],
                    'P-value': term[2],
                    'Adjusted P-value': term[6],
                    'Combined Score': term[4],
                    'Genes': ';'.join(term[5])
                })
            
            df = pd.DataFrame(results)
            all_results[library] = df
            
            print(f"  ✅ Found {len(data[library])} enriched terms")
            print(f"  Top term: {results[0]['Term']} (p={results[0]['Adjusted P-value']:.2e})")
        else:
            print(f"  ⚠️ No enrichment found")
    
    # Save results
    print("\n=== Saving Results ===")
    
    # Create combined table
    combined_results = []
    for library, df in all_results.items():
        df['Library'] = library
        combined_results.append(df)
    
    if combined_results:
        combined_df = pd.concat(combined_results, ignore_index=True)
        combined_df = combined_df.sort_values('Adjusted P-value')
        
        # Save full results
        combined_df.to_csv("reports/tables/pathway_enrichment_full.csv", index=False)
        print("✅ Saved: reports/tables/pathway_enrichment_full.csv")
        
        # Save top 20 for manuscript
        top20 = combined_df.head(20)[['Library', 'Term', 'Adjusted P-value', 'Combined Score', 'Genes']]
        top20.to_csv("reports/tables/pathway_enrichment_top20.csv", index=False)
        print("✅ Saved: reports/tables/pathway_enrichment_top20.csv")
        
        # Display top 10
        print("\n=== Top 10 Enriched Pathways ===")
        display_df = combined_df.head(10)[['Library', 'Term', 'Adjusted P-value']].copy()
        display_df['Adjusted P-value'] = display_df['Adjusted P-value'].apply(lambda x: f'{x:.2e}')
        print(display_df.to_string(index=False))
        
        # Save individual library results
        for library, df in all_results.items():
            safe_name = library.replace('_', '-').replace(' ', '-')
            df.to_csv(f"reports/tables/enrichment_{safe_name}.csv", index=False)
            print(f"✅ Saved: reports/tables/enrichment_{safe_name}.csv")
    else:
        print("⚠️ No enrichment results to save")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nNote: Enrichr API may be temporarily unavailable.")
    print("You can manually upload genes to: https://maayanlab.cloud/Enrichr/")
    print(f"\nGene list ({len(gene_symbols)} genes):")
    print('\n'.join(gene_symbols))

print("\n=== Pathway Enrichment Complete ===")
