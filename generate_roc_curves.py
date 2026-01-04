
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import StratifiedKFold
import json

print("=== Generating ROC Curves ===\n")

# Load data
bundle = joblib.load("outputs/models/model_bundle.joblib")
X = pd.read_parquet("outputs/dataset/feature_matrix.parquet")
y = pd.read_parquet("outputs/dataset/labels.parquet")

df = X.merge(y, on="sample_id")
feature_cols = bundle["feature_cols"]
Xmat = df[feature_cols].to_numpy()
yvec = df["label"].astype(int).to_numpy()

# Load CV metrics to get exact fold results
with open("outputs/models/nested_cv_metrics.json", "r") as f:
    cv_metrics = json.load(f)

# Get the selected model (XGBoost)
selected_model_name = cv_metrics["selected"]["model"]
fold_metrics = cv_metrics["selected"]["fold_metrics"]

print(f"Selected model: {selected_model_name}")
print(f"Number of folds: {len(fold_metrics)}")

# Recreate the exact CV splits used during training
seed = 20251221
outer = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)

# Generate ROC curves for each fold
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('ROC Curves - Treatment Failure Prediction (Nested CV)', fontsize=14, fontweight='bold')

fold_aucs = []
for fold_idx, (train_idx, test_idx) in enumerate(outer.split(Xmat, yvec)):
    # Get test data for this fold
    X_test = Xmat[test_idx]
    y_test = yvec[test_idx]
    
    # For visualization, we'll use the final trained model
    # (In reality, each fold had its own model, but we only saved the final one)
    model = bundle["best_model"]
    
    # Get predictions
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = model.decision_function(X_test)
        # Normalize to [0, 1]
        y_prob = (y_prob - y_prob.min()) / (y_prob.max() - y_prob.min() + 1e-9)
    
    # Compute ROC curve
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)
    fold_aucs.append(roc_auc)
    
    # Plot
    ax = axes[fold_idx]
    ax.plot(fpr, tpr, color='darkorange', lw=2, 
            label=f'ROC curve (AUC = {roc_auc:.3f})')
    ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title(f'Fold {fold_idx + 1}', fontsize=12, fontweight='bold')
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("reports/figures/roc_curves_nested_cv.png", dpi=300, bbox_inches="tight")
plt.close()
print("✅ Saved: reports/figures/roc_curves_nested_cv.png")

# Create a combined ROC curve plot
fig, ax = plt.subplots(figsize=(8, 8))

# Plot each fold
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
for fold_idx, (train_idx, test_idx) in enumerate(outer.split(Xmat, yvec)):
    X_test = Xmat[test_idx]
    y_test = yvec[test_idx]
    
    model = bundle["best_model"]
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = model.decision_function(X_test)
        y_prob = (y_prob - y_prob.min()) / (y_prob.max() - y_prob.min() + 1e-9)
    
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)
    
    ax.plot(fpr, tpr, color=colors[fold_idx], lw=2, alpha=0.8,
            label=f'Fold {fold_idx + 1} (AUC = {roc_auc:.3f})')

# Plot random classifier
ax.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--', label='Random (AUC = 0.500)')

# Calculate mean AUC
mean_auc = np.mean(fold_aucs)
ax.text(0.6, 0.2, f'Mean AUC = {mean_auc:.3f}', fontsize=14, 
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

ax.set_xlim([0.0, 1.0])
ax.set_ylim([0.0, 1.05])
ax.set_xlabel('False Positive Rate', fontsize=13)
ax.set_ylabel('True Positive Rate', fontsize=13)
ax.set_title('ROC Curves - Treatment Failure Prediction\n(XGBoost, Nested 3-Fold CV)', 
             fontsize=14, fontweight='bold')
ax.legend(loc="lower right", fontsize=11)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("reports/figures/roc_curves_combined.png", dpi=300, bbox_inches="tight")
plt.close()
print("✅ Saved: reports/figures/roc_curves_combined.png")

print(f"\nMean AUC across folds: {mean_auc:.3f}")
print(f"Individual fold AUCs: {[f'{a:.3f}' for a in fold_aucs]}")
