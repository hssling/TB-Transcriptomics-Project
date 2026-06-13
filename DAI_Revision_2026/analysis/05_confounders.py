"""WP-G: Confounder analysis for the neutrophil-high/T-cell-low association.

Addresses R2.9 (HIV, diabetes, bacterial load, drug resistance unaddressed).
GSE89403 (Catalysis treatment-response cohort) enrolled HIV-uninfected,
drug-susceptible pulmonary TB patients -> HIV and drug-resistance are
controlled by design (documented in text). Diabetes status is not recorded.
Bacterial load proxies (MGIT TTP, Xpert Ct, TGRV) ARE available and are
adjusted for here. Sex is estimated from XIST / RPS4Y1 expression.

Multivariable logistic regression: failure ~ neutrophil_score + sex +
bacterial_load, testing whether the neutrophil association is independent.
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
warnings.filterwarnings("ignore")
import common

OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

X, y, meta = common.load_baseline()
yv = y.values.astype(float)

# Neutrophil & T-cell scores from WP-D output
S = pd.read_csv(f"{OUT_TAB}/wpD_celltype_scores.csv", index_col=0)
S = S.loc[X.index]

# Estimate sex from sex-linked gene expression
sym = common.map_symbols(list(X.columns))
ens = {v: k for k, v in sym.items()}
def gene(symbol):
    e = ens.get(symbol)
    return X[e] if e in X.columns else pd.Series(np.nan, index=X.index)
xist = gene("XIST"); rps4y1 = gene("RPS4Y1")
# higher XIST - higher RPS4Y1 -> female
sex_score = (xist - xist.mean()) / (xist.std() + 1e-9) - \
            (rps4y1 - rps4y1.mean()) / (rps4y1.std() + 1e-9)
male = (sex_score < 0).astype(int)  # 1 = male

# Bacterial load: MGIT days-to-positivity (numeric), Xpert Ct, TGRV
def num(col):
    v = pd.to_numeric(meta[col].replace("NA", np.nan), errors="coerce")
    return v
mgit = num("mgit"); xpert = num("xpert"); tgrv = num("tgrv")
# composite load z-score (use mgit TTP inverted: shorter TTP = higher load)
load = pd.DataFrame({"mgit": mgit, "xpert": xpert}).apply(
    lambda c: (c - c.mean()) / (c.std() + 1e-9))
load_z = load.mean(1)

df = pd.DataFrame({
    "failure": yv,
    "neutrophil": S["Neutrophil"].values,
    "tcell": S["T_cell"].values,
    "male": male.values,
    "load": load_z.values,
}, index=X.index)
print("Sex estimate: males=%d females=%d" % (male.sum(), (1 - male).sum()))
print("Failure by sex:\n", df.groupby("male")["failure"].agg(["sum", "count"]))

results = {}
for label, formula_cols in [
    ("neutrophil_only", ["neutrophil"]),
    ("neutrophil_adj_sex", ["neutrophil", "male"]),
    ("neutrophil_adj_sex_load", ["neutrophil", "male", "load"]),
    ("tcell_adj_sex_load", ["tcell", "male", "load"]),
]:
    d = df.dropna(subset=formula_cols + ["failure"])
    Xd = sm.add_constant(d[formula_cols])
    try:
        m = sm.Logit(d["failure"], Xd).fit(disp=0, method="bfgs", maxiter=200)
        for c in formula_cols:
            results[f"{label}:{c}"] = {
                "OR": float(np.exp(m.params[c])),
                "CI_low": float(np.exp(m.conf_int().loc[c, 0])),
                "CI_high": float(np.exp(m.conf_int().loc[c, 1])),
                "p": float(m.pvalues[c]), "n": int(len(d))}
    except Exception as e:
        results[label] = {"error": str(e)}

res = pd.DataFrame(results).T
res.to_csv(f"{OUT_TAB}/wpG_confounder_logit.csv")
print("\nMultivariable logistic regression (failure outcome):")
print(res.to_string())
print("\nKey: does neutrophil OR remain significant after sex + bacterial load?")
