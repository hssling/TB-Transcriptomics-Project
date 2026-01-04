"""
Download and process GSE193979 for external validation.

GSE193979: "Transcriptional profiles predict treatment outcome in patients 
with tuberculosis and diabetes" (PMID: 35841871)

This dataset has actual treatment outcome labels (good/poor) - ideal for 
validating our treatment failure prediction signature.
"""

import os
import sys
import gzip
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
import urllib.request

# Configuration
GEO_ID = "GSE193979"
OUTPUT_DIR = Path("outputs/validation")
GEO_DATA_DIR = Path("geo_data")

# GEO FTP URLs
MATRIX_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE193nnn/GSE193979/matrix/GSE193979_series_matrix.txt.gz"
SUPPL_URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE193nnn/GSE193979/suppl/GSE193979_TANDEM_longitudinal_paper2_rawdata.txt.gz"

def download_file(url, dest_path):
    """Download file from URL with progress indicator."""
    print(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"  -> Saved to {dest_path}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def parse_series_matrix(gz_path):
    """Parse GEO series matrix file to extract metadata."""
    print(f"Parsing series matrix: {gz_path}")
    
    metadata = {}
    
    with gzip.open(gz_path, 'rt', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Extract sample IDs
            if line.startswith('!Sample_geo_accession'):
                parts = line.split('\t')
                sample_ids = [p.strip('"') for p in parts[1:]]
                metadata['sample_id'] = sample_ids
                
            # Extract sample titles
            elif line.startswith('!Sample_title'):
                parts = line.split('\t')
                titles = [p.strip('"') for p in parts[1:]]
                metadata['title'] = titles
                
            # Extract sample characteristics (contains outcome labels)
            elif line.startswith('!Sample_characteristics_ch1'):
                parts = line.split('\t')
                chars = [p.strip('"') for p in parts[1:]]
                
                # Parse characteristic type from first value
                if chars and ':' in chars[0]:
                    char_type = chars[0].split(':')[0].strip().lower().replace(' ', '_')
                    char_values = [c.split(':')[-1].strip() if ':' in c else c for c in chars]
                    metadata[char_type] = char_values
            
            # Stop at data section
            elif line.startswith('!series_matrix_table_begin'):
                break
    
    df = pd.DataFrame(metadata)
    return df

def parse_expression_matrix(gz_path, meta_df):
    """Parse expression matrix from supplementary file."""
    print(f"Parsing expression matrix: {gz_path}")
    
    # Read the raw data file
    with gzip.open(gz_path, 'rt') as f:
        df = pd.read_csv(f, sep='\t', index_col=0)
    
    print(f"  Raw matrix shape: {df.shape}")
    
    # The matrix is genes x samples, transpose to samples x genes
    df_t = df.T
    df_t.index.name = 'sample_id'
    df_t = df_t.reset_index()
    
    print(f"  Transposed shape: {df_t.shape}")
    
    return df_t

def extract_outcome_labels(meta_df):
    """Extract treatment outcome labels from metadata."""
    print("Extracting treatment outcome labels...")
    
    # Look for outcome-related columns
    outcome_cols = [c for c in meta_df.columns if 'outcome' in c.lower() or 'treatment' in c.lower()]
    print(f"  Found outcome columns: {outcome_cols}")
    
    # Create label column
    # Expected values: 'Good', 'Poor' or similar
    if 'treatment_outcome' in meta_df.columns:
        outcome_col = 'treatment_outcome'
    elif 'outcome' in meta_df.columns:
        outcome_col = 'outcome'
    else:
        # Try to find it in other characteristic columns
        for col in meta_df.columns:
            unique_vals = meta_df[col].unique()
            if any('good' in str(v).lower() or 'poor' in str(v).lower() for v in unique_vals):
                outcome_col = col
                break
        else:
            print("  WARNING: No clear outcome column found, checking all characteristics...")
            outcome_col = None
    
    if outcome_col:
        print(f"  Using column: {outcome_col}")
        print(f"  Unique values: {meta_df[outcome_col].unique()}")
        
        # Map to binary labels
        def map_outcome(val):
            val_lower = str(val).lower()
            if 'poor' in val_lower or 'fail' in val_lower or 'unfavor' in val_lower:
                return 1  # Treatment failure
            elif 'good' in val_lower or 'success' in val_lower or 'favor' in val_lower or 'cure' in val_lower:
                return 0  # Treatment success
            else:
                return None
        
        meta_df['label'] = meta_df[outcome_col].apply(map_outcome)
        
    return meta_df

def filter_baseline_samples(meta_df):
    """Filter to baseline (pre-treatment) samples only."""
    print("Filtering to baseline samples...")
    
    # Look for timepoint columns
    time_cols = [c for c in meta_df.columns if 'time' in c.lower() or 'visit' in c.lower() or 'week' in c.lower()]
    print(f"  Timepoint columns: {time_cols}")
    
    baseline_df = meta_df.copy()
    
    for col in time_cols:
        unique_vals = meta_df[col].unique()
        print(f"  {col}: {unique_vals}")
        
        # Filter for baseline/week0/diagnosis samples
        baseline_mask = meta_df[col].apply(
            lambda x: any(t in str(x).lower() for t in ['baseline', 'week0', 'week 0', 'diagnosis', 'day0', 'day 0', 'pre'])
        )
        if baseline_mask.any():
            baseline_df = meta_df[baseline_mask]
            print(f"  Filtered to {len(baseline_df)} baseline samples")
            break
    
    return baseline_df

def main():
    """Main function to download and process GSE193979."""
    print("=" * 60)
    print(f"Downloading and Processing {GEO_ID}")
    print("=" * 60)
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GEO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download files
    matrix_gz = GEO_DATA_DIR / f"{GEO_ID}_series_matrix.txt.gz"
    suppl_gz = GEO_DATA_DIR / f"{GEO_ID}_rawdata.txt.gz"
    
    if not matrix_gz.exists():
        download_file(MATRIX_URL, matrix_gz)
    else:
        print(f"Using cached: {matrix_gz}")
    
    if not suppl_gz.exists():
        download_file(SUPPL_URL, suppl_gz)
    else:
        print(f"Using cached: {suppl_gz}")
    
    # Parse metadata
    meta_df = parse_series_matrix(matrix_gz)
    print(f"\nMetadata shape: {meta_df.shape}")
    print(f"Metadata columns: {list(meta_df.columns)}")
    
    # Extract outcome labels
    meta_df = extract_outcome_labels(meta_df)
    
    # Filter to baseline samples
    baseline_meta = filter_baseline_samples(meta_df)
    
    # Check for valid labels
    labeled_samples = baseline_meta[baseline_meta['label'].notna()]
    print(f"\nBaseline samples with outcome labels: {len(labeled_samples)}")
    
    if len(labeled_samples) > 0:
        print(f"  Failures (label=1): {(labeled_samples['label'] == 1).sum()}")
        print(f"  Success (label=0): {(labeled_samples['label'] == 0).sum()}")
    
    # Parse expression data if available
    if suppl_gz.exists():
        try:
            expr_df = parse_expression_matrix(suppl_gz, meta_df)
            
            # Save outputs
            expr_output = OUTPUT_DIR / f"{GEO_ID}_expression.parquet"
            meta_output = OUTPUT_DIR / f"{GEO_ID}_metadata.parquet"
            
            expr_df.to_parquet(expr_output, index=False)
            baseline_meta.to_parquet(meta_output, index=False)
            
            print(f"\nSaved expression data: {expr_output}")
            print(f"Saved metadata: {meta_output}")
            
        except Exception as e:
            print(f"\nError parsing expression data: {e}")
            print("Will attempt to use series matrix data...")
    
    # Also save full metadata for inspection
    full_meta_output = OUTPUT_DIR / f"{GEO_ID}_full_metadata.csv"
    meta_df.to_csv(full_meta_output, index=False)
    print(f"Saved full metadata: {full_meta_output}")
    
    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    
    return labeled_samples

if __name__ == "__main__":
    result = main()
    if result is not None and len(result) > 0:
        print("\n✅ Successfully prepared validation cohort")
        sys.exit(0)
    else:
        print("\n⚠️  Need to check metadata format manually")
        sys.exit(1)
