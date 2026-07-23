"""Is the end-of-treatment signal simply the known active-tuberculosis signature?

Published signatures that separate active disease from latent infection or
health are among the most reproducible findings in tuberculosis transcriptomics.
If patients recorded as not cured still carry active disease at the end of
therapy, those signatures should separate them from cured patients without any
model being fitted at all.

Testing that directly does two things. It benchmarks our model-derived signal
against established, externally validated tools rather than against itself, and
it tells us how much of the week-24 result is a rediscovery of known biology
versus something new.
"""
import json
import warnings

import common2 as C

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")

# Published signatures, expressed as up-weighted and down-weighted members.
SIGNATURES = {
    "Sweeney 3-gene": {"up": ["GBP5", "DUSP3"], "down": ["KLF2"]},
    "Berry 393-gene core (interferon module)": {
        "up": ["FCGR1A", "FCGR1B", "GBP1", "GBP2", "GBP5", "GBP6", "STAT1",
               "STAT2", "IFIT1", "IFIT2", "IFIT3", "IFI44", "IFI44L", "IFI6",
               "MX1", "OAS1", "OAS2", "OAS3", "ISG15", "RSAD2", "SERPING1",
               "BATF2", "ANKRD22", "C1QB", "SEPT4", "VAMP5", "METTL7B"],
        "down": []},
    "Kaforou 44-gene (myeloid up / lymphoid down)": {
        "up": ["FCGR1A", "GBP6", "BATF2", "ANKRD22", "SERPING1", "VAMP5",
               "C1QB", "STAT1", "GBP5", "SEPT4"],
        "down": ["CD3D", "CD3E", "CD79A", "MS4A1", "TCF7", "CCR7", "IL7R",
                 "KLRB1", "GNLY"]},
    "Zak 16-gene risk (interferon-dominated)": {
        "up": ["GBP2", "FCGR1A", "SERPING1", "TRAFD1", "STAT1", "BATF2",
               "GBP1", "ANKRD22"],
        "down": ["BLK", "CD79A", "FCGR1CP", "SCARF1"]},
}


def score(X, sig, s2e):
    """Mean z-score of up-weighted members minus down-weighted members."""
    Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)

    def cols(symbols):
        out = []
        for g in symbols:
            out.extend([e for e in s2e.get(g, []) if e in Xz.columns])
        return out

    up, dn = cols(sig["up"]), cols(sig["down"])
    if not up:
        return None, 0, 0
    s = Xz[up].mean(1)
    if dn:
        s = s - Xz[dn].mean(1)
    return s, len(up), len(dn)


def main():
    s2e = C.symbol_to_ensembl()
    rows = []
    for arm in C.ARMS:
        X, y, meta = C.load_arm(arm)
        for name, sig in SIGNATURES.items():
            s, n_up, n_dn = score(X, sig, s2e)
            if s is None:
                continue
            a, b = s[y.values == 1], s[y.values == 0]
            u, p = mannwhitneyu(a, b, alternative="two-sided")
            r = 2 * u / (len(a) * len(b)) - 1
            auc = roc_auc_score(y.values, s.values)
            rows.append({
                "arm": arm, "arm_label": C.ARM_LABEL[arm], "signature": name,
                "genes_up": n_up, "genes_down": n_dn,
                "rank_biserial_r": float(r), "p_value": float(p),
                "roc_auc": float(auc)})

    t = pd.DataFrame(rows)
    t.to_csv(f"{C.TAB}/established_signatures.csv", index=False)

    for arm in C.ARMS:
        print(f"\n=== {C.ARM_LABEL[arm]} ===")
        sub = t[t.arm == arm][["signature", "roc_auc", "rank_biserial_r",
                               "p_value"]]
        print(sub.to_string(index=False))

    # How does an unfitted published signature compare with our fitted model?
    M = json.load(open(f"{C.TAB}/arm_metrics.json"))
    print("\n=== published signature vs fitted model, by arm ===")
    cmp_rows = []
    for arm in C.ARMS:
        best = M[arm]["models"][M[arm]["best_model"]]["roc_auc"]
        top = t[t.arm == arm].nlargest(1, "roc_auc").iloc[0]
        cmp_rows.append({"arm": C.ARM_LABEL[arm],
                         "fitted_model_auc": round(best, 3),
                         "best_published_signature": top.signature,
                         "published_auc": round(top.roc_auc, 3),
                         "difference": round(best - top.roc_auc, 3)})
    c = pd.DataFrame(cmp_rows)
    print(c.to_string(index=False))
    c.to_csv(f"{C.TAB}/signature_vs_model.csv", index=False)
    print("\nwrote established_signatures.csv and signature_vs_model.csv")


if __name__ == "__main__":
    main()
