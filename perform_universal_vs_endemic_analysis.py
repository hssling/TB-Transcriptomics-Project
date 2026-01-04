
import GEOparse
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix
import ast
import os

# --- 1. Load Datasets ---
def load_dataset(gse_id, label_parser):
    print(f"Loading {gse_id}...")
    try:
        gse = GEOparse.get_GEO(geo=gse_id, destdir="./geo_data", silent=True)
        # Expression Data
        if gse.gpls:
            print(f"  {gse_id} has platform data.")
        
        # MergeGSMs (samples) into a DataFrame
        # Ideally, we used pivot_samples from GEOparse but let's do manual extraction to be safe
        # expression_data = gse.pivot_samples('VALUE') # This often fails if columns mismatch
        
        # Let's try simple pivot
        df_expr = gse.pivot_samples('VALUE').T
        print(f"  Expression Shape: {df_expr.shape}")
        
        # Extract Labels
        labels = []
        keep_indices = []
        
        for idx, gsm_name in enumerate(df_expr.index):
            gsm = gse.gsms[gsm_name]
            label = label_parser(gsm.metadata)
            if label:
                labels.append(label)
                keep_indices.append(idx)
        
        df_expr = df_expr.iloc[keep_indices]
        cleaned_labels = labels
        
        print(f"  Kept {len(cleaned_labels)} samples with valid labels.")
        return df_expr, pd.Series(cleaned_labels, index=df_expr.index)
        
    except Exception as e:
        print(f"  Error loading {gse_id}: {e}")
        return None, None

# --- 2. Label Parsers ---

def parser_london(meta):
    # GSE107991
    # Check 'source_name_ch1' or 'characteristics_ch1'
    # Source names were: 'Berry_London_Test_set_Active_TB', 'Berry_London_Test_set_LTBI', 'Berry_London_Test_set_Control'
    # We want Active vs LTBI (Ignore Control for strict TB vs LTBI test, or include? Usually TB vs LTBI is the clinical challenge)
    # Let's stick to TB vs LTBI as per standard diagnostic goal.
    try:
        source = meta.get('source_name_ch1', [''])[0]
        if 'Active_TB' in source:
            return 1 # Positive Class
        elif 'LTBI' in source:
            return 0 # Negative Class
        return None
    except:
        return None

def parser_india(meta):
    # GSE101705
    # characteristics_ch1: ['condition: TB', 'condition: latent TB infection']
    try:
        # In GEOparse, if it's a single value, it might be a list of 1 string
        chars = meta.get('characteristics_ch1', [])
        # Flatten if it's a list of lists or just check content
        char_str = str(chars) 
        
        if 'condition: TB' in char_str:
            return 1
        elif 'condition: latent TB infection' in char_str:
            return 0
        return None
    except:
        return None

# --- 3. Main Analysis ---
def main():
    # Load London (Train)
    X_train_raw, y_train = load_dataset("GSE107991", parser_london)
    if X_train_raw is None: return

    # Load India (Test)
    X_test_raw, y_test = load_dataset("GSE101705", parser_india)
    if X_test_raw is None: return
    
    # Align Genes (Intersection)
    common_genes = X_train_raw.columns.intersection(X_test_raw.columns)
    print(f"\nAligning datasets on {len(common_genes)} common genes...")
    
    X_train = X_train_raw[common_genes]
    X_test = X_test_raw[common_genes]
    
    # Fill NAs (if any)
    X_train = X_train.fillna(0)
    X_test = X_test.fillna(0)
    
    # --- 4. Training (London) ---
    print("\nTraining Random Forest on London Cohort (Active vs LTBI)...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    
    # CV Performance
    cv_scores = cross_val_score(clf, X_train, y_train, cv=5, scoring='roc_auc')
    print(f"London Cross-Validation AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")
    
    # Train full model
    clf.fit(X_train, y_train)
    
    # --- 5. Validating (India) ---
    print("\nValidating on Independent India Cohort...")
    y_pred_prob = clf.predict_proba(X_test)[:, 1]
    y_pred = clf.predict(X_test)
    
    india_auc = roc_auc_score(y_test, y_pred_prob)
    india_acc = accuracy_score(y_test, y_pred)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    
    print(f"India Validation AUC: {india_auc:.3f}")
    print(f"India Accuracy: {india_acc:.3f}")
    print(f"India Sensitivity: {sensitivity:.3f}")
    print(f"India Specificity: {specificity:.3f}")
    
    # --- 6. Interpretation ---
    delta = cv_scores.mean() - india_auc
    print(f"\nPerformance Drop (Generalization Gap): {delta:.3f}")
    if delta > 0.1:
        print("CONCLUSION: Significant generalization gap observed. Supports 'Endemic' hypothesis.")
    else:
        print("CONCLUSION: Model generalizes well. Challenges 'Endemic' hypothesis.")

if __name__ == "__main__":
    main()
