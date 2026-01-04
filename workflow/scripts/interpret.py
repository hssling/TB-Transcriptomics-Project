import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import matplotlib.pyplot as plt
import gseapy as gp

try:
    import shap
except Exception:
    shap = None

cfg = snakemake.config
X = pd.read_parquet(snakemake.input["X"])
y = pd.read_parquet(snakemake.input["y"])
meta = pd.read_parquet(snakemake.input["meta"])
bundle = joblib.load(snakemake.input["bundle"])

df = X.merge(y, on="sample_id", how="inner").merge(meta, on="sample_id", how="inner")
val_cohort = cfg["external_validation_cohort"]
train_df = df[df["cohort_id"] != val_cohort].copy()

fc = bundle["feature_cols"]
model = bundle["best_model"]
best_name = bundle["best_model_name"]

Xtr = train_df[fc]
ytr = train_df["label"].astype(int).to_numpy()

Path("reports/figures").mkdir(parents=True, exist_ok=True)
Path("reports/tables").mkdir(parents=True, exist_ok=True)

top_features = []
shap_success = False

# Try SHAP
if shap is not None and best_name in ("random_forest", "xgboost"):
    try:
        print("Calculating SHAP values...")
        # For large feature sets, sample rows for speed
        Xs = Xtr.sample(n=min(500, len(Xtr)), random_state=int(cfg.get("random_seed", 42)))
        
        # Determine explainer
        explainer = shap.Explainer(model, Xs, feature_names=fc)
        shap_values = explainer(Xs)
        
        # Handle SHAP values shape (list vs array)
        vals = shap_values.values
        if isinstance(vals, list):
            # For binary classification, sometimes returns list of [neg, pos]. Take pos.
            vals = vals[1]
        elif len(vals.shape) == 3 and vals.shape[2] == 2:
             vals = vals[:, :, 1]
             
        mean_abs = np.abs(vals).mean(axis=0)
        imp = pd.DataFrame({"feature": fc, "mean_abs_shap": mean_abs}).sort_values("mean_abs_shap", ascending=False)
        top_features = imp.head(50)["feature"].tolist()

        # Plot
        plt.figure()
        shap.summary_plot(shap_values, Xs, show=False)
        plt.savefig(snakemake.output[0], dpi=200, bbox_inches="tight")
        plt.close()
        shap_success = True
    except Exception as e:
        print(f"SHAP calculation failed: {e}")
        shap_success = False

if not shap_success:
    print("Using feature extraction fallback...")
    # Logistic: coefficients if available
    try:
        if hasattr(model, "coef_"):
            coef = np.ravel(model.coef_)
            if len(coef) == len(fc):
                imp = pd.DataFrame({"feature": fc, "coef": coef, "abs_coef": np.abs(coef)}).sort_values("abs_coef", ascending=False)
                top_features = imp.head(50)["feature"].tolist()
            else:
                 raise ValueError("Coef shape mismatch")
        elif hasattr(model, "feature_importances_"):
             fi = model.feature_importances_
             imp = pd.DataFrame({"feature": fc, "importance": fi}).sort_values("importance", ascending=False)
             top_features = imp.head(50)["feature"].tolist()
        else:
            # fallback: feature variance
            imp = pd.DataFrame({"feature": fc, "var": Xtr.var().values}).sort_values("var", ascending=False)
            top_features = imp.head(50)["feature"].tolist()
    except Exception as e:
        print(f"Fallback feature ranking failed: {e}")
        top_features = fc[:50] # Desperate fallback

    # Create a simple placeholder plot
    plt.figure()
    plt.text(0.5, 0.5, "SHAP / Feature Importance Unavailable", ha='center', va='center')
    plt.axis("off")
    plt.savefig(snakemake.output[0], dpi=200, bbox_inches="tight")
    plt.close()

pd.DataFrame({"feature": top_features}).to_csv(snakemake.output[1], index=False)

# Enrichment (Enrichr): use top features as gene symbols if they look like symbols
libs = cfg.get("enrichr", {}).get("libraries", ["Reactome_2022"])
genes = [g for g in top_features if isinstance(g, str) and len(g) > 1]
enrich_rows = []
if genes:
    for lib in libs:
        try:
            enr = gp.enrichr(gene_list=genes, gene_sets=lib, organism="Human", outdir=None, cutoff=0.5)
            if enr is not None and hasattr(enr, "results") and enr.results is not None:
                r = enr.results.copy()
                r["library"] = lib
                enrich_rows.append(r)
        except Exception:
            continue

if enrich_rows:
    try:
        out = pd.concat(enrich_rows, ignore_index=True)
        # Keep top 30 by adjusted p
        if "Adjusted P-value" in out.columns:
            out = out.sort_values("Adjusted P-value").head(30)
        out.to_csv(snakemake.output[2], index=False)
    except Exception as e:
        pd.DataFrame({"note": [f"Enrichment merge failed: {e}"]}).to_csv(snakemake.output[2], index=False)
else:
    pd.DataFrame({"note": ["Enrichment could not be computed (gene IDs may not be symbols)."]}).to_csv(snakemake.output[2], index=False)
