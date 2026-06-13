"""WP-C: SHAP interpretation of the baseline XGBoost model + full feature list.

Addresses R2.5 (SHAP-based interpretation), R2.4 (full feature list with
symbols accessible), R3.3 (how feature importance was conducted).

We refit the XGBoost model on all 90 baseline samples using univariate
pre-selection (top-K), then compute TreeExplainer SHAP values. The ranked
feature list (with HGNC symbols) is exported in full.
"""
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
from sklearn.feature_selection import SelectKBest, f_classif
from xgboost import XGBClassifier
warnings.filterwarnings("ignore")
import common

OUT_FIG = f"{common.ROOT}/DAI_Revision_2026/figures"
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

X, y, meta = common.load_baseline()
yv = y.values
K = 50  # parsimonious panel for interpretation
spw = (yv == 0).sum() / max(1, (yv == 1).sum())

sel = SelectKBest(f_classif, k=K).fit(X.values, yv)
feat_idx = sel.get_support(indices=True)
feat_names = X.columns[feat_idx]
Xs = pd.DataFrame(X.values[:, feat_idx], columns=feat_names, index=X.index)

model = XGBClassifier(n_estimators=120, max_depth=3, learning_rate=0.05,
                      subsample=0.8, colsample_bytree=0.6, scale_pos_weight=spw,
                      eval_metric="logloss", random_state=20260613, n_jobs=-1)
model.fit(Xs.values, yv)

explainer = shap.TreeExplainer(model)
sv = explainer.shap_values(Xs.values)
mean_abs = np.abs(sv).mean(0)

sym = common.map_symbols(list(feat_names))
imp = pd.DataFrame({"ensembl": feat_names,
                    "gene_symbol": [sym[g] for g in feat_names],
                    "mean_abs_shap": mean_abs,
                    "univariate_F": sel.scores_[feat_idx]})
imp = imp.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
imp.to_csv(f"{OUT_TAB}/wpC_shap_feature_list.csv", index=False)
print("Top 15 SHAP features:")
print(imp.head(15).to_string(index=False))

# Flag Y-linked genes among top predictors (R3.4 evidence)
yl = imp[imp["gene_symbol"].isin(["RPS4Y1", "KDM5D", "DDX3Y", "UTY",
                                  "USP9Y", "EIF1AY", "NLGN4Y", "TXLNGY"])]
print("\nY-linked among selected predictors:")
print(yl.to_string(index=False) if len(yl) else "  none in top-K panel")

# SHAP summary (beeswarm) with gene symbols
Xs_named = Xs.copy()
Xs_named.columns = [sym[g] for g in feat_names]
plt.figure()
shap.summary_plot(sv, Xs_named, max_display=15, show=False)
plt.title("SHAP summary — baseline failure-risk model", fontsize=12)
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure_shap_summary.png", dpi=300, bbox_inches="tight")
plt.close()

# SHAP bar
plt.figure(figsize=(8, 6))
top = imp.head(15).iloc[::-1]
plt.barh(top["gene_symbol"], top["mean_abs_shap"], color="#4477aa")
plt.xlabel("Mean |SHAP value|", fontsize=12)
plt.title("Top 15 predictors of baseline TB treatment-failure risk", fontsize=12)
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure_shap_bar.png", dpi=300)
plt.close()
print("\nSaved SHAP figures + wpC_shap_feature_list.csv")
