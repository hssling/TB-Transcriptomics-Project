"""
Search for suitable GEO datasets for TB outcome prediction external validation
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Candidate datasets based on literature
candidate_datasets = [
    # Treatment outcome studies
    "GSE107991",  # TB treatment response
    "GSE107994",  # TB treatment outcomes
    "GSE107995",  # TB treatment monitoring
    "GSE19491",   # TB progression
    "GSE19444",   # TB infection outcomes
    "GSE28623",   # TB treatment response
    "GSE39939",   # TB treatment outcomes
    "GSE39940",   # TB treatment response
    "GSE62525",   # TB progression risk
    "GSE79362",   # TB treatment outcomes
    "GSE94438",   # TB treatment response
    "GSE101705",  # TB treatment outcomes
    "GSE116015",  # TB treatment response
    "GSE139825",  # TB progression
    "GSE152532",  # TB treatment outcomes
]

def get_geo_info(gse_id):
    """Fetch basic info about a GEO dataset"""
    url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get title
            title_elem = soup.find('td', string='Title')
            title = title_elem.find_next_sibling('td').text.strip() if title_elem else "N/A"
            
            # Get summary
            summary_elem = soup.find('td', string='Summary')
            summary = summary_elem.find_next_sibling('td').text.strip() if summary_elem else "N/A"
            
            # Get organism
            organism_elem = soup.find('td', string='Organism')
            organism = organism_elem.find_next_sibling('td').text.strip() if organism_elem else "N/A"
            
            # Get platform
            platform_elem = soup.find('td', string='Platforms')
            platform = platform_elem.find_next_sibling('td').text.strip() if platform_elem else "N/A"
            
            # Get sample count
            samples_elem = soup.find('td', string='Samples')
            samples = samples_elem.find_next_sibling('td').text.strip() if samples_elem else "N/A"
            
            return {
                'GSE': gse_id,
                'Title': title,
                'Summary': summary[:200] + "..." if len(summary) > 200 else summary,
                'Organism': organism,
                'Platform': platform,
                'Samples': samples
            }
        else:
            return {'GSE': gse_id, 'Title': 'ERROR', 'Summary': f'HTTP {response.status_code}', 
                    'Organism': 'N/A', 'Platform': 'N/A', 'Samples': 'N/A'}
    except Exception as e:
        return {'GSE': gse_id, 'Title': 'ERROR', 'Summary': str(e), 
                'Organism': 'N/A', 'Platform': 'N/A', 'Samples': 'N/A'}

print("Searching for suitable TB outcome GEO datasets...\n")
results = []

for gse in candidate_datasets:
    print(f"Checking {gse}...")
    info = get_geo_info(gse)
    results.append(info)
    time.sleep(1)  # Be nice to NCBI servers

# Create DataFrame
df = pd.DataFrame(results)
df.to_csv('geo_candidate_datasets.csv', index=False)

print("\n" + "="*80)
print("RESULTS:")
print("="*80)
print(df.to_string())

print("\n\nRecommended datasets for external validation:")
print("-" * 80)
for idx, row in df.iterrows():
    if any(keyword in row['Summary'].lower() for keyword in ['treatment', 'outcome', 'progression', 'response']):
        print(f"\n{row['GSE']}: {row['Title']}")
        print(f"  Samples: {row['Samples']}")
        print(f"  Summary: {row['Summary']}")
