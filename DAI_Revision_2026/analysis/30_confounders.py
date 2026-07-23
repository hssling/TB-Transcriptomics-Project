"""Whether the immune association survives adjustment, in every arm.

Sex is inferred from XIST and RPS4Y1 expression because it is not deposited,
and bacterial load is represented by the culture and molecular measures
recorded at diagnosis. The source cohort enrolled HIV-negative, rifampicin-
susceptible patients, so those two factors are fixed by the study design
rather than modelled. Diabetes status was not recorded.

Sex-linked transcripts also dominate an unadjusted feature ranking when the
unfavourable group is small and skewed by sex, so they are tested directly for
differential expression as a check on that artefact.
"""
import warnings

import common2 as C

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

Y_LINKED = ["RPS4Y1", "KDM5D", "DDX3Y", "UTY", "USP9Y", "EIF1AY", "NLGN4Y",
            "TXLNGY"]


def gene_series(X, symbol, s2e):
    for e in s2e.get(symbol, []):
        if e in X.columns:
            return X[e]
    return pd.Series(np.nan, index=X.index)


def infer_sex(X, s2e):
    xist = gene_series(X, "XIST", s2e)
    rps4y1 = gene_series(X, "RPS4Y1", s2e)
    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    score = z(xist) - z(rps4y1)
    return (score < 0).astype(int)          # 1 = male


def main():
    s2e = C.symbol_to_ensembl()
    deg = pd.read_csv(f"{C.TAB}/deg_all_arms.csv")
    rows, sex_rows, ylinked_rows = [], [], []

    for arm in C.ARMS:
        X, y, meta = C.load_arm(arm)
        S, _ = C.celltype_scores(X)
        male = infer_sex(X, s2e)

        load = pd.DataFrame({
            "mgit": pd.to_numeric(meta["mgit"], errors="coerce"),
            "xpert": pd.to_numeric(meta["xpert"], errors="coerce")})
        load = load.apply(lambda c: (c - c.mean()) / (c.std() + 1e-9))
        load_z = load.mean(axis=1)

        df = pd.DataFrame({
            "outcome": y.values.astype(float),
            "neutrophil": S["Neutrophil"].values,
            "tcell": S["T_cell"].values,
            "male": male.values,
            "load": load_z.values,
        }, index=X.index)

        n_male_fail = int(df.loc[df.outcome == 1, "male"].sum())
        n_fail = int(df.outcome.sum())
        sex_rows.append({"arm": arm, "arm_label": C.ARM_LABEL[arm],
                         "males": int(df["male"].sum()),
                         "females": int((1 - df["male"]).sum()),
                         "male_among_unfavourable": f"{n_male_fail}/{n_fail}"})

        for label, cols in [("Neutrophil, unadjusted", ["neutrophil"]),
                            ("Neutrophil, adjusted for sex", ["neutrophil", "male"]),
                            ("Neutrophil, adjusted for sex and bacterial load",
                             ["neutrophil", "male", "load"]),
                            ("T cell, adjusted for sex and bacterial load",
                             ["tcell", "male", "load"])]:
            d = df.dropna(subset=cols + ["outcome"])
            if d["outcome"].nunique() < 2 or len(d) < 20:
                continue
            try:
                fit = sm.Logit(d["outcome"], sm.add_constant(d[cols])).fit(
                    disp=0, method="bfgs", maxiter=400)
                ci = fit.conf_int()
                key = cols[0]
                rows.append({
                    "arm": arm, "arm_label": C.ARM_LABEL[arm], "model": label,
                    "term": key, "n": int(len(d)),
                    "odds_ratio": float(np.exp(fit.params[key])),
                    "ci_low": float(np.exp(ci.loc[key, 0])),
                    "ci_high": float(np.exp(ci.loc[key, 1])),
                    "p_value": float(fit.pvalues[key]),
                })
            except Exception as exc:
                rows.append({"arm": arm, "arm_label": C.ARM_LABEL[arm],
                             "model": label, "term": cols[0],
                             "n": int(len(d)), "odds_ratio": np.nan,
                             "ci_low": np.nan, "ci_high": np.nan,
                             "p_value": np.nan, "note": type(exc).__name__})

        d = deg[(deg.arm == arm) & (deg.gene_symbol.isin(Y_LINKED))]
        for _, r in d.iterrows():
            ylinked_rows.append({"arm": arm, "arm_label": C.ARM_LABEL[arm],
                                 "gene_symbol": r.gene_symbol,
                                 "log2_fold_change": r.log2_fold_change,
                                 "p_value": r.p_value, "fdr": r.fdr})

    conf = pd.DataFrame(rows)
    conf.to_csv(f"{C.TAB}/confounder_models.csv", index=False)
    pd.DataFrame(sex_rows).to_csv(f"{C.TAB}/sex_distribution.csv", index=False)
    pd.DataFrame(ylinked_rows).to_csv(f"{C.TAB}/y_linked_genes.csv", index=False)

    print(conf.to_string(index=False))
    print()
    print(pd.DataFrame(sex_rows).to_string(index=False))
    print("\nY-linked transcripts, differential expression by outcome:")
    yl = pd.DataFrame(ylinked_rows)
    print(yl.groupby("arm_label")["p_value"].agg(["min", "count"]).to_string())
    print("\nwrote confounder_models.csv, sex_distribution.csv, y_linked_genes.csv")


if __name__ == "__main__":
    main()
