"""Feature attribution for the gradient-boosted model in each arm.

Gradient boosting is the attribution vehicle because TreeExplainer returns
exact Shapley values for additive tree ensembles, so the ranking carries no
approximation error of its own. The accompanying benchmark records how the
three candidate classifiers compare within each arm, which is the evidence for
that choice rather than an assertion of it.

The ranked panel written here is the input to pathway enrichment (25) and to
the conditional-dependency network (26), keeping one feature set flowing
through the whole pipeline.
"""
import json
import warnings

import common2 as C

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.feature_selection import SelectKBest, f_classif
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

K_PANEL = 50      # interpretable panel size
N_TOP = 25        # genes carried into enrichment and the network


def fit_panel(X, y):
    yv = y.values
    spw = (yv == 0).sum() / max(1, (yv == 1).sum())
    sel = SelectKBest(f_classif, k=K_PANEL).fit(X.values, yv)
    idx = sel.get_support(indices=True)
    names = X.columns[idx]
    Xs = pd.DataFrame(X.values[:, idx], columns=names, index=X.index)
    model = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.6,
                          scale_pos_weight=spw, eval_metric="logloss",
                          random_state=C.SEED, n_jobs=1, verbosity=0)
    model.fit(Xs.values, yv)
    return model, Xs, sel.scores_[idx]


def main():
    metrics = json.load(open(f"{C.TAB}/arm_metrics.json"))
    all_imp = []
    fig, axes = plt.subplots(1, len(C.ARMS), figsize=(5.0 * len(C.ARMS), 7.0))

    for j, arm in enumerate(C.ARMS):
        X, y, meta = C.load_arm(arm)
        model, Xs, fscores = fit_panel(X, y)
        sv = shap.TreeExplainer(model).shap_values(Xs.values)
        mean_abs = np.abs(sv).mean(0)
        # Direction of association, read the way a beeswarm plot is read: the
        # rank correlation between a gene's expression and the SHAP value it
        # receives. Positive means higher expression pushes the prediction
        # towards an unfavourable outcome. An absolute offset in the SHAP
        # baseline, which the class imbalance induces, cancels out.
        direction = []
        for k in range(Xs.shape[1]):
            col = Xs.values[:, k]
            if np.std(col) < 1e-12 or np.std(sv[:, k]) < 1e-12:
                direction.append(0.0)
            else:
                direction.append(float(spearmanr(col, sv[:, k]).statistic))

        imp = pd.DataFrame({
            "arm": arm, "arm_label": C.ARM_LABEL[arm],
            "ensembl": Xs.columns,
            "gene_symbol": C.to_symbols(list(Xs.columns)),
            "mean_abs_shap": mean_abs,
            "shap_direction_high_expression": direction,
            "univariate_F": fscores,
        }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
        imp["rank"] = np.arange(1, len(imp) + 1)
        all_imp.append(imp)

        print(f"\n=== {C.ARM_LABEL[arm]} : top 12 by mean |SHAP| ===")
        print(imp.head(12)[["rank", "gene_symbol", "mean_abs_shap",
                            "shap_direction_high_expression"]].to_string(index=False))

        ax = axes[j]
        top = imp.head(15).iloc[::-1]
        cols = ["#C44E52" if d > 0 else "#4C72B0"
                for d in top["shap_direction_high_expression"]]
        ax.barh(np.arange(len(top)), top["mean_abs_shap"], color=cols)
        ax.set_yticks(np.arange(len(top)))
        ax.set_yticklabels(top["gene_symbol"], fontsize=9)
        ax.set_xlabel("mean |SHAP|", fontsize=9)
        ax.set_title(C.ARM_LABEL[arm], fontsize=12, fontweight="bold")
        if j == 0:
            handles = [plt.Rectangle((0, 0), 1, 1, color="#C44E52"),
                       plt.Rectangle((0, 0), 1, 1, color="#4C72B0")]
            ax.legend(handles, ["High expression raises risk",
                                "High expression lowers risk"],
                      fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{C.FIG}/Figure_shap_arms.png", dpi=300)
    plt.close(fig)

    imp_all = pd.concat(all_imp, ignore_index=True)
    imp_all.to_csv(f"{C.TAB}/shap_feature_ranking.csv", index=False)
    imp_all[imp_all["rank"] <= N_TOP].to_csv(f"{C.TAB}/shap_top_features.csv",
                                             index=False)

    # ---- Benchmark supporting the gradient-boosting choice ----
    bench = []
    for arm in [a for a in C.ARMS + ["combined"] if a in metrics]:
        for name, res in metrics[arm]["models"].items():
            bench.append({"arm": C.ARM_LABEL[arm], "model": name,
                          "roc_auc": res["roc_auc"],
                          "ci_low": res["roc_auc_ci"][0],
                          "ci_high": res["roc_auc_ci"][1],
                          "pr_auc": res["pr_auc"], "mcc": res["mcc"],
                          "brier": res["brier"]})
    pd.DataFrame(bench).to_csv(f"{C.TAB}/model_benchmark.csv", index=False)
    print("\nwrote shap_feature_ranking.csv, shap_top_features.csv, "
          "model_benchmark.csv and Figure_shap_arms.png")


if __name__ == "__main__":
    main()
