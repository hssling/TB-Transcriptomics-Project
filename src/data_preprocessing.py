"""
Prepare GSE107991 data for external validation
This script downloads and prepares GSE107991 (Berry London cohort) for use as external validation
"""
import pandas as pd
import os
from pathlib import Path

# Use the already downloaded data
geo_data_dir = Path("geo_data")
metadata_file = geo_data_dir / "GSE107991_metadata.csv"

if not metadata_file.exists():
    print(f"Error: {metadata_file} not found!")
    print("Please run check_gse107991.py first to download the metadata")
    exit(1)

# Load metadata
df = pd.read_csv(metadata_file)

print(f"Loaded {len(df)} samples from GSE107991")
print(f"\nGroup distribution:")
print(df['group'].value_counts())

# Map groups to labels
label_map = {
    'Active_TB': 1,  # Poor outcome / disease progression
    'LTBI': 0,       # Good outcome / no active disease  
    'Control': 0     # Good outcome / healthy
}

df['label'] = df['group'].map(label_map)

# Check for any unmapped values
unmapped = df[df['label'].isna()]
if len(unmapped) > 0:
    print(f"\nWarning: {len(unmapped)} samples with unmapped groups:")
    print(unmapped['group'].value_counts())
else:
    print("\nOK - All samples successfully mapped to labels")

print(f"\nLabel distribution:")
print(df['label'].value_counts())
print(f"\n  Label 0 (Good outcome): {(df['label']==0).sum()} samples")
print(f"  Label 1 (Poor outcome): {(df['label']==1).sum()} samples")

# Save prepared metadata
output_dir = Path("outputs/metadata")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "gse107991_prepared.csv"
df.to_csv(output_file, index=False)

print(f"\nOK - Prepared metadata saved to {output_file}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Dataset: GSE107991 (Berry London cohort)")
print(f"Total samples: {len(df)}")
print(f"Active TB (label=1): {(df['label']==1).sum()}")
print(f"LTBI + Control (label=0): {(df['label']==0).sum()}")
print(f"\nThis dataset will be used for external validation of the TB outcome prediction model.")
print(f"The model trained on GSE89403 (South Africa, treatment outcomes) will be tested on")
print(f"GSE107991 (London, diagnostic classification) to assess generalizability.")
