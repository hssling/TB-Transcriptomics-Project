"""WP-F: External-validation attempt + documented exclusion table.

Reviewer 2 explicitly allowed: validate on an independent GEO cohort OR
formally document that no suitable dataset exists with a supplementary
exclusion table. We did a genuine search; the closest candidate
(GSE193979, TANDEM SA+Indonesia treatment-outcome RNA-seq) cannot be used
for OUTCOME-stratified validation from public data because:
  (i) per-patient treatment-outcome labels are NOT deposited in GEO; and
  (ii) the public count matrix is keyed by internal 'RSEQ' IDs with no public
       bridge to the GSM/patient identifiers that carry any metadata.
We therefore (a) build a transparent exclusion table, and (b) still run a
label-free SIGNATURE-PORTABILITY check on GSE193979 diagnosis samples to show
the deconvolution signature computes and reproduces the expected
neutrophil<->T-cell anti-structure in an independent cohort.
"""
import gzip
import warnings
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
warnings.filterwarnings("ignore")
import common

OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"
EXT = f"{common.ROOT}/DAI_Revision_2026/external"

# ---- (a) Exclusion / candidate-cohort justification table ----
rows = [
    {"cohort": "GSE89403 (Catalysis, Thompson 2017)",
     "n": "254 (DX baseline 90)", "outcome_labels": "Yes (Cure/Not-Cured)",
     "role": "DISCOVERY cohort (this study)",
     "suitable_external": "No - discovery"},
    {"cohort": "GSE193979 (TANDEM, SA+Indonesia 2022)",
     "n": "~175 samples / 63 patients", "outcome_labels": "Good/Poor (paper only)",
     "role": "Closest treatment-outcome RNA-seq cohort",
     "suitable_external": "No - per-patient outcome NOT in GEO; count matrix keyed "
     "by internal RSEQ IDs with no public bridge to GSM/patient metadata"},
    {"cohort": "GSE107994 (Leicester, Singhania 2018)",
     "n": "175", "outcome_labels": "Progression (ATB/LTBI), not treatment outcome",
     "role": "TB progression", "suitable_external": "No - outcome mismatch "
     "(progression, not treatment failure)"},
    {"cohort": "GSE79362 (ACS, Zak 2016)",
     "n": "~355", "outcome_labels": "Progression to active TB",
     "role": "TB progression", "suitable_external": "No - outcome mismatch"},
    {"cohort": "GSE107991 (Berry/London)",
     "n": "54", "outcome_labels": "ATB vs LTBI", "role": "TB status",
     "suitable_external": "No - no treatment-outcome labels"},
]
ex = pd.DataFrame(rows)
ex.to_csv(f"{OUT_TAB}/wpF_external_exclusion_table.csv", index=False)
print("Exclusion table:\n", ex.to_string(index=False))

# ---- (b) Label-free signature-portability check on GSE193979 ----
MARKERS = {
    "Neutrophil": ["FCGR3B", "CSF3R", "CXCR2", "CXCR1", "S100A8", "S100A9",
                   "S100A12", "MPO", "ELANE", "FUT4", "CEACAM3", "FFAR2",
                   "MMP8", "MMP9", "LCN2", "CAMP", "LTF", "BPI"],
    "T_cell": ["CD3D", "CD3E", "CD3G", "CD2", "CD28", "IL7R", "CD8A", "CD8B",
               "LCK", "TRAC", "CCR7", "CD27", "CD5", "TCF7"],
}
try:
    df = pd.read_csv(f"{EXT}/GSE193979_rawdata.txt.gz", sep="\t", index_col=0)
    print(f"\nGSE193979 matrix: {df.shape[0]} genes x {df.shape[1]} samples")
    # CPM log1p
    cpm = df / df.sum(0) * 1e6
    logx = np.log1p(cpm)
    z = logx.sub(logx.mean(1), 0).div(logx.std(1) + 1e-9, 0)  # gene z across samples
    sym = common.map_symbols(list(df.index))
    s2e = {}
    for e, s in sym.items():
        s2e.setdefault(s, []).append(e)
    scores = {}
    for cell, genes in MARKERS.items():
        ens = [g for gg in genes for g in s2e.get(gg, []) if g in z.index]
        scores[cell] = z.loc[ens].mean(0)
    S = pd.DataFrame(scores).T  # cell x sample
    rho, p = spearmanr(S.loc["Neutrophil"], S.loc["T_cell"])
    print(f"Portability check (independent cohort GSE193979):")
    print(f"  Neutrophil vs T-cell score Spearman rho = {rho:.2f} (p={p:.1e})")
    print(f"  -> Expected biological anti-structure {'REPRODUCED' if rho < 0 else 'NOT reproduced'}")
    out = {"cohort": "GSE193979", "n_samples": int(df.shape[1]),
           "neutrophil_vs_tcell_spearman": float(rho), "p": float(p),
           "note": "label-free portability; outcome-stratified validation not "
                   "possible from public data (see exclusion table)"}
    import json
    json.dump(out, open(f"{OUT_TAB}/wpF_portability.json", "w"), indent=2)
except Exception as e:
    print("Portability check failed:", e)

print("\nSaved wpF_external_exclusion_table.csv + wpF_portability.json")
