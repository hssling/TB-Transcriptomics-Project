"""WP-E: Cell-type specificity validation in a GRANULOCYTE-CONTAINING reference.

Replaces the inappropriate PBMC3k validation (R2.6: PBMC3k lacks neutrophils
due to density-gradient isolation). We use the Human Protein Atlas (HPA) blood
atlas (Uhlen et al., immune-cell consensus including neutrophils) to show that:
 - the Neutrophil failure-signature genes are specifically expressed in
   neutrophils, and
 - the T-cell failure-signature genes are specifically expressed in T cells.
Output: a labeled cell-type x signature-gene nTPM heatmap with a real scale
(R3: Fig3 needs cell labels + scale).
"""
import json
import ssl
import time
import urllib.request
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
import common

OUT_FIG = f"{common.ROOT}/DAI_Revision_2026/figures"
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"
ctx = ssl.create_default_context(); ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

NEUTRO_SIG = ["MPO", "ELANE", "FCGR3B", "S100A8", "S100A9", "S100A12",
              "CSF3R", "CXCR2", "MMP8", "MMP9", "LCN2", "CAMP"]
TCELL_SIG = ["CD3D", "CD3E", "CD2", "IL7R", "CD8A", "CD8B", "LCK", "TRAC",
             "CCR7", "TCF7"]
SYM2ENS = {"MPO": "ENSG00000005381", "ELANE": "ENSG00000197561",
           "FCGR3B": "ENSG00000162747", "S100A8": "ENSG00000143546",
           "S100A9": "ENSG00000163220", "S100A12": "ENSG00000163221",
           "CSF3R": "ENSG00000119535", "CXCR2": "ENSG00000180871",
           "MMP8": "ENSG00000118113", "MMP9": "ENSG00000100985",
           "LCN2": "ENSG00000148346", "CAMP": "ENSG00000164047",
           "CD3D": "ENSG00000167286", "CD3E": "ENSG00000198851",
           "CD2": "ENSG00000116824", "IL7R": "ENSG00000168685",
           "CD8A": "ENSG00000153563", "CD8B": "ENSG00000172116",
           "LCK": "ENSG00000182866", "TRAC": "ENSG00000277734",
           "CCR7": "ENSG00000126353", "TCF7": "ENSG00000081059"}


def hpa_blood(ensg):
    url = f"https://www.proteinatlas.org/{ensg}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, context=ctx, timeout=60).read())
    return d.get("RNA blood cell specific nTPM") or d.get("blood cell specific nTPM")


records = {}
for sym in NEUTRO_SIG + TCELL_SIG:
    ensg = SYM2ENS.get(sym)
    if not ensg:
        continue
    try:
        bc = hpa_blood(ensg)
        if isinstance(bc, dict):
            records[sym] = bc
    except Exception as e:
        print("warn", sym, str(e)[:60])
    time.sleep(0.3)

mat = pd.DataFrame(records).T  # genes x cell types
mat = mat.apply(pd.to_numeric, errors="coerce").fillna(0)
mat.to_csv(f"{OUT_TAB}/wpE_hpa_celltype_nTPM.csv")
print("Cell types in HPA blood atlas:", list(mat.columns))

# collapse to lineage groups for clarity
def grp(col):
    c = col.lower()
    if "neutro" in c: return "Neutrophil"
    if "eosino" in c: return "Eosinophil"
    if "basoph" in c: return "Basophil"
    if "t-cell" in c or "t cell" in c or "treg" in c or "mait" in c or "gdt" in c: return "T cell"
    if "b-cell" in c or "b cell" in c or "plasma" in c or "memory b" in c or "naive b" in c: return "B cell"
    if "nk" in c: return "NK cell"
    if "mono" in c or "dendritic" in c or "dc" == c: return "Monocyte/DC"
    return "Other"
groups = pd.Series({c: grp(c) for c in mat.columns})
lin = mat.T.groupby(groups).max().T  # max nTPM per lineage
order = [g for g in ["Neutrophil", "Eosinophil", "Basophil", "Monocyte/DC",
                     "T cell", "B cell", "NK cell", "Other"] if g in lin.columns]
lin = lin[order]
# row-normalize for specificity display
linn = lin.div(lin.max(1) + 1e-9, 0)

fig, ax = plt.subplots(figsize=(8, 9))
im = ax.imshow(linn.values, aspect="auto", cmap="magma")
ax.set_xticks(range(len(order))); ax.set_xticklabels(order, rotation=40, ha="right", fontsize=11)
ax.set_yticks(range(len(linn))); ax.set_yticklabels(linn.index, fontsize=10)
# divider between neutrophil and T-cell signature genes
nb = len([g for g in NEUTRO_SIG if g in linn.index])
ax.axhline(nb - 0.5, color="cyan", lw=2)
ax.text(-0.6, (nb - 1) / 2, "Neutrophil\nsignature", rotation=90, va="center",
        ha="center", fontsize=10, color="#444")
ax.text(-0.6, nb + (len(linn) - nb - 1) / 2, "T-cell\nsignature", rotation=90,
        va="center", ha="center", fontsize=10, color="#444")
cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cb.set_label("Relative expression (row-max normalised nTPM)", fontsize=11)
ax.set_title("Cell-type specificity of failure-signature genes\n"
             "(Human Protein Atlas blood atlas; includes neutrophils)", fontsize=12)
plt.tight_layout()
plt.savefig(f"{OUT_FIG}/Figure3_celltype_specificity.png", dpi=300)
plt.close()

# Quantify specificity: fraction of neutrophil-sig genes max-expressed in neutrophils
neu_genes = [g for g in NEUTRO_SIG if g in lin.index]
t_genes = [g for g in TCELL_SIG if g in lin.index]
neu_hit = sum(lin.loc[g].idxmax() == "Neutrophil" for g in neu_genes)
t_hit = sum(lin.loc[g].idxmax() == "T cell" for g in t_genes)
print(f"\nNeutrophil-signature genes max-expressed in neutrophils: {neu_hit}/{len(neu_genes)}")
print(f"T-cell-signature genes max-expressed in T cells: {t_hit}/{len(t_genes)}")
json.dump({"neutrophil_specific": f"{neu_hit}/{len(neu_genes)}",
           "tcell_specific": f"{t_hit}/{len(t_genes)}",
           "reference": "Human Protein Atlas blood atlas (granulocyte-containing)"},
          open(f"{OUT_TAB}/wpE_specificity_summary.json", "w"), indent=2)
print("Saved Figure3_celltype_specificity.png + wpE tables")
