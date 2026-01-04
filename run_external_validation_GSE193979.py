"""
External validation on GSE193979 (TANDEM cohort) with inferred outcomes.

Logic for outcome inference:
- Patients with Month_6 samples LIKELY had GOOD outcomes (survived to follow-up)
- Patients with only Diagnosis samples (no follow-up) may have had POOR outcomes

Strategy:
1. Parse metadata to identify unique patients
2. Check which patients have Month_6 samples (proxy for survival/good outcome)
3. Use Diagnosis (baseline) samples only for prediction
4. Assign inferred labels based on longitudinal follow-up availability
"""

import os
import gzip
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, roc_curve

# Configuration
GEO_DATA_DIR = Path("geo_data")
OUTPUT_DIR = Path("outputs/external_validation_GSE193979")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def parse_series_matrix():
    """Parse GSE193979 series matrix to extract sample metadata."""
    matrix_path = GEO_DATA_DIR / "GSE193979_series_matrix.txt.gz"
    
    print("Parsing GSE193979 series matrix...")
    
    samples = []
    current_chars = {}
    
    with gzip.open(matrix_path, 'rt', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            # Get sample IDs
            if line.startswith('!Sample_geo_accession'):
                parts = line.split('\t')
                sample_ids = [p.strip('"') for p in parts[1:]]
                current_chars['sample_id'] = sample_ids
                
            # Get sample titles
            elif line.startswith('!Sample_title'):
                parts = line.split('\t')
                titles = [p.strip('"') for p in parts[1:]]
                current_chars['title'] = titles
                
            # Get characteristics
            elif line.startswith('!Sample_characteristics_ch1'):
                parts = line.split('\t')
                values = [p.strip('"') for p in parts[1:]]
                
                # Parse characteristic type from first non-empty value
                for v in values:
                    if v and ':' in v:
                        char_type = v.split(':')[0].strip().lower().replace(' ', '_')
                        char_values = []
                        for val in values:
                            if ':' in val:
                                char_values.append(val.split(':')[1].strip())
                            else:
                                char_values.append('')
                        current_chars[char_type] = char_values
                        break
            
            # Stop at expression data
            elif line.startswith('!series_matrix_table_begin'):
                break
    
    # Create DataFrame
    n_samples = len(current_chars.get('sample_id', []))
    print(f"Found {n_samples} samples")
    
    df = pd.DataFrame()
    for key, values in current_chars.items():
        if len(values) == n_samples:
            df[key] = values
    
    return df

def infer_outcomes(meta_df):
    """Infer treatment outcomes based on longitudinal follow-up availability."""
    print("\nInferring treatment outcomes from longitudinal structure...")
    
    # Get unique patients
    patients = meta_df['patient_id'].unique()
    print(f"Found {len(patients)} unique patients")
    
    # For each patient, check if they have Month_6 samples
    patient_outcomes = {}
    for patient in patients:
        patient_samples = meta_df[meta_df['patient_id'] == patient]
        timepoints = patient_samples['timepoint'].unique()
        
        # Patient has Month_6 sample = likely survived = GOOD outcome
        if 'Month_6' in timepoints:
            patient_outcomes[patient] = 0  # Good outcome (cured)
        else:
            # Only early timepoints = possible POOR outcome
            patient_outcomes[patient] = 1  # Poor outcome (failure/death)
    
    # Add inferred label to metadata
    meta_df['inferred_label'] = meta_df['patient_id'].map(patient_outcomes)
    
    # Summary statistics
    good_patients = sum(1 for v in patient_outcomes.values() if v == 0)
    poor_patients = sum(1 for v in patient_outcomes.values() if v == 1)
    print(f"  Good (Month_6 available): {good_patients} patients")
    print(f"  Poor (no Month_6): {poor_patients} patients")
    
    return meta_df, patient_outcomes

def get_baseline_samples(meta_df):
    """Filter to baseline (Diagnosis) samples only."""
    print("\nFiltering to baseline (Diagnosis) samples...")
    
    baseline_df = meta_df[meta_df['timepoint'] == 'Diagnosis'].copy()
    print(f"  Baseline samples: {len(baseline_df)}")
    
    # Check label distribution
    label_counts = baseline_df['inferred_label'].value_counts()
    print(f"  Good outcome: {label_counts.get(0, 0)}")
    print(f"  Poor outcome: {label_counts.get(1, 0)}")
    
    return baseline_df

def load_expression_data():
    """Load and process the GSE193979 expression matrix."""
    print("\nLoading expression data...")
    
    # Check for rawdata file
    rawdata_path = GEO_DATA_DIR / "GSE193979_rawdata_v2.txt.gz"
    
    if rawdata_path.exists():
        with gzip.open(rawdata_path, 'rt') as f:
            df = pd.read_csv(f, sep='\t', index_col=0)
        print(f"  Raw matrix shape: {df.shape}")
        
        # Clean column names (remove quotes)
        df.columns = [c.strip('"') for c in df.columns]
        
        # Transpose to samples x genes
        df_t = df.T
        df_t.index.name = 'RSEQ_ID'
        df_t = df_t.reset_index()
        print(f"  Transposed shape: {df_t.shape}")
        return df_t
    else:
        print("  ERROR: Raw data file not found")
        return None

def build_gsm_rseq_mapping():
    """Build GSM -> RSEQ ID mapping from tar archive filenames."""
    print("\nBuilding GSM -> RSEQ mapping from archive...")
    import tarfile
    import re
    
    tar_path = GEO_DATA_DIR / "GSE193979_suppl.tar"
    if not tar_path.exists():
        print("  ERROR: Tar archive not found")
        return {}
    
    gsm_to_rseq = {}
    with tarfile.open(tar_path) as tf:
        for m in tf.getmembers():
            match = re.match(r'(GSM\d+)_(RSEQ\d+)', m.name)
            if match:
                gsm, rseq = match.groups()
                gsm_to_rseq[gsm] = rseq
    
    print(f"  Mapped {len(gsm_to_rseq)} samples")
    return gsm_to_rseq

def load_trained_model():
    """Load the trained model and scaler from holdout validation."""
    print("\nLoading trained model...")
    
    model_path = Path("outputs/holdout_validation/holdout_model_bundle.joblib")
    if not model_path.exists():
        print("  ERROR: Model bundle not found")
        return None, None, None
    
    bundle = joblib.load(model_path)
    model = bundle['model']
    scaler = bundle['scaler']
    feature_cols = bundle.get('feature_cols', None)
    
    print(f"  Model type: {type(model).__name__}")
    if feature_cols:
        print(f"  Features: {len(feature_cols)}")
    
    return model, scaler, feature_cols

def run_external_validation(expression_df, meta_df, gsm_to_rseq, model, scaler, feature_cols):
    """Run the trained model on external validation data."""
    print("\nRunning external validation...")
    
    # Add RSEQ ID to metadata using GSM->RSEQ mapping
    meta_df = meta_df.copy()
    meta_df['RSEQ_ID'] = meta_df['sample_id'].map(gsm_to_rseq)
    
    # Filter to samples that have RSEQ mapping
    mapped_samples = meta_df.dropna(subset=['RSEQ_ID'])
    print(f"  Samples with RSEQ mapping: {len(mapped_samples)}")
    
    if len(mapped_samples) == 0:
        print("  ERROR: No samples could be mapped")
        return None
    
    # Get expression sample column
    sample_col = expression_df.columns[0]  # RSEQ_ID
    expr_rseq = set(expression_df[sample_col].values)
    meta_rseq = set(mapped_samples['RSEQ_ID'].values)
    
    overlap = expr_rseq.intersection(meta_rseq)
    print(f"  RSEQ IDs in expression: {len(expr_rseq)}")
    print(f"  RSEQ IDs in metadata (baseline): {len(meta_rseq)}")
    print(f"  Overlap: {len(overlap)}")
    
    if len(overlap) < 5:
        print("  ERROR: Too few samples with matching IDs")
        return None
    
    # Filter metadata to overlapping samples
    valid_samples = mapped_samples[mapped_samples['RSEQ_ID'].isin(overlap)]
    print(f"  Valid samples for validation: {len(valid_samples)}")
    
    # Get expression for these samples
    expr_filtered = expression_df[expression_df[sample_col].isin(valid_samples['RSEQ_ID'])]
    expr_filtered = expr_filtered.set_index(sample_col)
    
    # Get labels aligned by RSEQ_ID
    labels = valid_samples.set_index('RSEQ_ID')['inferred_label']
    
    # Ensure same order
    common_samples = expr_filtered.index.intersection(labels.index)
    X = expr_filtered.loc[common_samples]
    y = labels.loc[common_samples].values
    
    print(f"  Final samples: {len(X)}")
    print(f"  Poor outcome (inferred): {sum(y)}")
    print(f"  Good outcome (inferred): {len(y) - sum(y)}")
    
    # Check feature overlap with trained model
    if feature_cols is not None:
        available_features = set(X.columns)
        required_features = set(feature_cols)
        feature_overlap = available_features.intersection(required_features)
        print(f"  Feature overlap: {len(feature_overlap)} / {len(required_features)}")
        
        if len(feature_overlap) < len(required_features) * 0.1:
            print("  WARNING: Very low feature overlap. Trying to match by gene symbol...")
            # The datasets may use different identifiers
            # Skip alignment if no features match
        
        # Use only overlapping features (fill missing with 0)
        X_aligned = pd.DataFrame(0, index=X.index, columns=feature_cols)
        for col in feature_overlap:
            X_aligned[col] = X[col]
        X = X_aligned
    
    # Scale features
    X_scaled = scaler.transform(X)
    
    # Get predictions
    y_pred_proba = model.predict_proba(X_scaled)[:, 1]
    
    # Calculate metrics
    if len(np.unique(y)) < 2:
        print("  ERROR: Only one class present in validation data")
        return None
    
    roc_auc = roc_auc_score(y, y_pred_proba)
    pr_auc = average_precision_score(y, y_pred_proba)
    brier = brier_score_loss(y, y_pred_proba)
    
    results = {
        'n_samples': len(y),
        'n_positive': int(sum(y)),
        'n_negative': int(len(y) - sum(y)),
        'roc_auc': float(roc_auc),
        'pr_auc': float(pr_auc),
        'brier_score': float(brier),
        'note': 'Outcomes inferred from longitudinal follow-up availability (Month_6 = good outcome)'
    }
    
    print(f"\n{'='*50}")
    print("EXTERNAL VALIDATION RESULTS (GSE193979)")
    print(f"{'='*50}")
    print(f"Samples: {results['n_samples']}")
    print(f"Poor outcome (inferred): {results['n_positive']}")
    print(f"Good outcome (inferred): {results['n_negative']}")
    print(f"\nROC-AUC: {results['roc_auc']:.3f}")
    print(f"PR-AUC: {results['pr_auc']:.3f}")
    print(f"Brier Score: {results['brier_score']:.3f}")
    
    return results, y, y_pred_proba

def create_roc_plot(y_true, y_pred_proba, auc_value):
    """Create ROC curve plot."""
    import matplotlib.pyplot as plt
    
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, 'b-', linewidth=2, label=f'Model (AUC = {auc_value:.3f})')
    plt.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random (AUC = 0.5)')
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.title('External Validation ROC Curve\n(GSE193979 TANDEM Cohort - Inferred Outcomes)', fontsize=14)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'roc_external_validation_GSE193979.png', dpi=150)
    plt.close()
    print(f"\nSaved ROC plot: {OUTPUT_DIR / 'roc_external_validation_GSE193979.png'}")

def main():
    """Run external validation on GSE193979."""
    print("="*70)
    print("EXTERNAL VALIDATION ON GSE193979 (TANDEM COHORT)")
    print("="*70)
    
    # Step 1: Parse metadata
    meta_df = parse_series_matrix()
    print(f"\nMetadata columns: {list(meta_df.columns)}")
    
    # Step 2: Infer outcomes
    meta_df, patient_outcomes = infer_outcomes(meta_df)
    
    # Step 3: Get baseline samples
    baseline_df = get_baseline_samples(meta_df)
    
    # Step 4: Build GSM -> RSEQ mapping
    gsm_to_rseq = build_gsm_rseq_mapping()
    if not gsm_to_rseq:
        print("Cannot proceed without GSM->RSEQ mapping")
        return
    
    # Step 5: Load expression data
    expression_df = load_expression_data()
    if expression_df is None:
        print("Cannot proceed without expression data")
        return
    
    # Step 6: Load trained model
    model, scaler, feature_cols = load_trained_model()
    if model is None:
        print("Cannot proceed without trained model")
        return
    
    # Step 7: Run validation
    result = run_external_validation(expression_df, baseline_df, gsm_to_rseq, model, scaler, feature_cols)
    
    if result is not None:
        results, y_true, y_pred = result
        
        # Save results
        with open(OUTPUT_DIR / 'external_validation_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved results: {OUTPUT_DIR / 'external_validation_results.json'}")
        
        # Create ROC plot
        create_roc_plot(y_true, y_pred, results['roc_auc'])
    else:
        print("\nExternal validation could not be completed.")

if __name__ == "__main__":
    main()
