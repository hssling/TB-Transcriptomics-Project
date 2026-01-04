
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
from pathlib import Path

print("=== Loading Model and Data ===")
bundle = joblib.load("outputs/models/model_bundle.joblib")
X = pd.read_parquet("outputs/dataset/feature_matrix.parquet")
y = pd.read_parquet("outputs/dataset/labels.parquet")

df = X.merge(y, on="sample_id")
feature_cols = bundle["feature_cols"]
Xmat = df[feature_cols].to_numpy()
yvec = df["label"].astype(int).to_numpy()

model = bundle["best_model"]
model_name = bundle["best_model_name"]

print(f"Best model: {model_name}")
print(f"Features: {len(feature_cols)}")
print(f"Samples: {len(yvec)}")

# Create SHAP explainer
print("\n=== Computing SHAP Values ===")
print("This may take a few minutes...")

# Use TreeExplainer for tree-based models, LinearExplainer for linear models
if model_name in ["random_forest", "xgboost"]:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(Xmat)
    
    # For binary classification, shap_values might be a list
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # Use positive class
else:
    # For logistic regression pipeline
    explainer = shap.LinearExplainer(model.named_steps['clf'], Xmat)
    shap_values = explainer.shap_values(Xmat)

print("SHAP values computed!")

# Create output directory
Path("reports/figures").mkdir(parents=True, exist_ok=True)

# 1. Summary plot
print("\n=== Generating SHAP Summary Plot ===")
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, Xmat, feature_names=feature_cols, show=False, max_display=20)
plt.tight_layout()
plt.savefig("reports/figures/shap_summary_plot.png", dpi=300, bbox_inches="tight")
plt.close()
print("✅ Saved: reports/figures/shap_summary_plot.png")

# 2. Bar plot of mean absolute SHAP values
print("\n=== Generating SHAP Feature Importance Bar Plot ===")
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, Xmat, feature_names=feature_cols, plot_type="bar", show=False, max_display=20)
plt.tight_layout()
plt.savefig("reports/figures/shap_importance_bar.png", dpi=300, bbox_inches="tight")
plt.close()
print("✅ Saved: reports/figures/shap_importance_bar.png")

# 3. Get top features
mean_abs_shap = np.abs(shap_values).mean(axis=0)
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'mean_abs_shap': mean_abs_shap
}).sort_values('mean_abs_shap', ascending=False)

# Save top features
Path("reports/tables").mkdir(parents=True, exist_ok=True)
feature_importance.head(50).to_csv("reports/tables/top_50_features_shap.csv", index=False)
print("✅ Saved: reports/tables/top_50_features_shap.csv")

print("\n=== Top 20 Features by SHAP ===")
print(feature_importance.head(20))

# 4. Individual dependence plots for top 3 features
print("\n=== Generating Dependence Plots for Top 3 Features ===")
for i, row in feature_importance.head(3).iterrows():
    feat = row['feature']
    feat_idx = feature_cols.index(feat)
    
    plt.figure(figsize=(8, 6))
    shap.dependence_plot(feat_idx, shap_values, Xmat, feature_names=feature_cols, show=False)
    plt.tight_layout()
    safe_name = feat.replace("/", "_").replace(":", "_")
    plt.savefig(f"reports/figures/shap_dependence_{safe_name}.png", dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved: reports/figures/shap_dependence_{safe_name}.png")

print("\n=== SHAP Analysis Complete ===")
print(f"Total plots generated: {3 + len(feature_importance.head(3))}")
