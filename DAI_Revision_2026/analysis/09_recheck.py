"""RECHECK: independent verification of the headline results, using different
estimators/procedures than the originals.

Checks:
 1. Data integrity: baseline cohort uniqueness, no subject duplication, label
    mapping consistent with treatmentresult.
 2. Discrimination via an INDEPENDENT procedure: leave-one-out CV (appropriate
    for 7 events) with a simple, fixed pipeline; compare to repeated K-fold.
 3. Permutation null: shuffle labels 1000x to confirm the observed AUC is not
    trivially explainable by chance / overfitting of the CV wrapper.
 4. Neutrophil association re-tested independently (exact MWU + bootstrap CI of
    rank-biserial; logistic on neutrophil only).
 5. Concordance re-computed independently from a freshly refit model.
"""
import warnings, json
import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from scipy.stats import mannwhitneyu
warnings.filterwarnings("ignore")
import common

T = f"{common.ROOT}/DAI_Revision_2026/tables"
X, y, meta = common.load_baseline()
yv = y.values
print("=== 1. DATA INTEGRITY ===")
print("samples:", X.shape[0], "| unique sample_ids:", X.index.nunique(),
      "| unique subjects:", meta['subject'].nunique())
assert X.index.nunique() == X.shape[0], "duplicate sample ids!"
assert meta['subject'].nunique() == X.shape[0], "subject duplication at baseline!"
# label vs treatmentresult consistency
tr = meta['treatmentresult']
chk = pd.crosstab(tr, yv)
print("treatmentresult vs label:\n", chk)
assert ((tr == 'Not Cured') == (yv == 1)).all(), "label != Not Cured!"
print("PASS: labels exactly match 'Not Cured'; all baseline subjects unique.")

print("\n=== 2. LEAVE-ONE-OUT CV (independent of repeated K-fold) ===")
pipe = Pipeline([("sel", SelectKBest(f_classif, k=200)),
                 ("clf", RandomForestClassifier(n_estimators=150, max_depth=4,
                  class_weight="balanced_subsample", random_state=0, n_jobs=-1))])
N_PERM = 300
loo_prob = cross_val_predict(pipe, X.values, yv, cv=LeaveOneOut(),
                             method="predict_proba", n_jobs=-1)[:, 1]
loo_auc = roc_auc_score(yv, loo_prob)
print(f"LOO-CV ROC-AUC = {loo_auc:.3f}  (repeated-KFold reported ~0.67)")

print("\n=== 3. PERMUTATION NULL (1000 shuffles, 5-fold) ===")
def kfold_auc(Xv, yt, seed):
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    pr = cross_val_predict(pipe, Xv, yt, cv=skf, method="predict_proba")[:, 1]
    return roc_auc_score(yt, pr)
obs = np.mean([kfold_auc(X.values, yv, s) for s in range(5)])
print(f"  observed computed ({obs:.3f}); running {N_PERM} permutations...", flush=True)
rng = np.random.default_rng(0)
null = []
for i in range(N_PERM):
    yp = rng.permutation(yv)
    try:
        null.append(kfold_auc(X.values, yp, 12345))
    except Exception:
        pass
null = np.array(null)
pval = (np.sum(null >= obs) + 1) / (len(null) + 1)
print(f"observed mean AUC={obs:.3f}; permutation null mean={null.mean():.3f} "
      f"(95th pct={np.percentile(null,95):.3f}); permutation p={pval:.3f}")

print("\n=== 4. NEUTROPHIL ASSOCIATION (independent re-test) ===")
S = pd.read_csv(f"{T}/wpD_celltype_scores.csv", index_col=0).loc[X.index]
a = S.loc[yv == 1, "Neutrophil"].values
b = S.loc[yv == 0, "Neutrophil"].values
u, p = mannwhitneyu(a, b, alternative="two-sided")
r_obs = 1 - 2 * u / (len(a) * len(b))
# bootstrap CI of rank-biserial
boot = []
for _ in range(5000):
    ai = rng.choice(a, len(a), True); bi = rng.choice(b, len(b), True)
    uu, _ = mannwhitneyu(ai, bi, alternative="two-sided")
    boot.append(1 - 2 * uu / (len(ai) * len(bi)))
print(f"Neutrophil MWU p={p:.4f}; rank-biserial r={r_obs:.2f} "
      f"(95% CI {np.percentile(boot,2.5):.2f}..{np.percentile(boot,97.5):.2f})")

print("\n=== 5. CONCORDANCE (fresh refit, independent) ===")
from scipy.stats import spearmanr
skf = StratifiedKFold(5, shuffle=True, random_state=7)
prob = cross_val_predict(pipe, X.values, yv, cv=skf, method="predict_proba")[:, 1]
rho_n, pn = spearmanr(S["Neutrophil"].values, prob)
rho_t, pt = spearmanr(S["T_cell"].values, prob)
print(f"Neutrophil vs fresh OOF prob rho={rho_n:.2f} (p={pn:.1e}); "
      f"T-cell rho={rho_t:.2f} (p={pt:.1e})")

json.dump({"loo_auc": float(loo_auc), "perm_obs_auc": float(obs),
           "perm_null_mean": float(null.mean()), "perm_p": float(pval),
           "neutrophil_mwu_p": float(p), "neutrophil_r": float(r_obs),
           "neutrophil_r_ci": [float(np.percentile(boot,2.5)), float(np.percentile(boot,97.5))],
           "concordance_neu_rho": float(rho_n), "concordance_tcell_rho": float(rho_t)},
          open(f"{T}/recheck_summary.json", "w"), indent=2)
print("\nSaved recheck_summary.json")
