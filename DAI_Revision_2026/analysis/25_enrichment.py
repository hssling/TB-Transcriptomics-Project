"""Pathway analysis of the features the model relies on.

Three complementary tests, because a fifty-gene panel is too small to support
open-ended over-representation testing on its own:

  A  Targeted test of the SHAP-ranked panel against six curated immune
     programmes. Restricting to a small, pre-specified set keeps the
     multiple-testing burden negligible and asks a question the data can
     answer.
  B  Open-ended enrichment on the genes that survive false-discovery
     correction in the differential-expression analysis, which is adequately
     powered wherever such genes exist.
  C  Open-ended enrichment on the SHAP panels, retained for completeness and
     reported in the supplement.
"""
import warnings

import common2 as C

import numpy as np
import pandas as pd
from scipy.stats import hypergeom
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")

GENE_SETS = ["GO_Biological_Process_2023", "KEGG_2021_Human",
             "MSigDB_Hallmark_2020", "Reactome_2022"]
TOP_N = 50
MAX_DEG = 1000

# Pre-specified immune programmes relevant to tuberculosis pathology.
PROGRAMMES = {
    "Neutrophil degranulation and effector function": [
        "FCGR3B", "CSF3R", "S100A8", "S100A9", "S100A12", "MPO", "ELANE",
        "LCN2", "CAMP", "LTF", "BPI", "DEFA1", "DEFA3", "DEFA4", "MMP8",
        "MMP9", "CEACAM8", "OLFM4", "ARG1", "CD177", "ALOX5AP", "FPR1",
        "SLPI", "CTSG", "PRTN3", "TCN1", "HP", "ORM1", "VNN1", "MMP25"],
    "T-cell receptor signalling and adaptive response": [
        "CD3D", "CD3E", "CD3G", "CD2", "CD28", "IL7R", "CD8A", "CD8B", "LCK",
        "TRAC", "TRBC2", "CCR7", "CD27", "CD5", "ITK", "TCF7", "ZAP70",
        "LAT", "THEMIS", "CD6", "CD247", "IL32", "CD40LG"],
    "Interferon-inducible response": [
        "GBP1", "GBP2", "GBP5", "STAT1", "STAT2", "IRF1", "IFIT1", "IFIT2",
        "IFIT3", "IFI44", "IFI44L", "IFI6", "MX1", "OAS1", "OAS2", "OAS3",
        "ISG15", "RSAD2", "SERPING1", "BATF2", "ANKRD22", "FCGR1A", "FCGR1B",
        "FCGR1CP", "VAMP5", "METTL7B", "SEPT4", "C1QB", "GCH1"],
    "Inflammatory and myeloid activation": [
        "IL1B", "IL1R2", "IL6", "TNF", "TLR2", "TLR4", "TLR5", "NLRP3",
        "CD14", "SOCS3", "NFKBIA", "PTX3", "SAA1", "SAA2", "CR1", "STOM",
        "PLAUR", "AQP9", "FAM20A", "CLEC4D", "CLEC4E", "IRAK3"],
    "Cytotoxic and natural-killer effector programme": [
        "GNLY", "NKG7", "PRF1", "GZMA", "GZMB", "GZMH", "GZMK", "KLRD1",
        "KLRF1", "NCR1", "NCAM1", "FGFBP2", "SPON2", "CX3CR1"],
    "B-cell and immunoglobulin programme": [
        "CD19", "MS4A1", "CD79A", "CD79B", "IGHM", "BANK1", "TCL1A", "IGLL5",
        "POU2AF1", "FCRL1", "TNFRSF13C"],
}


def targeted(genes, universe):
    """Hypergeometric over-representation against the curated programmes."""
    uni = set(universe)
    drawn = set(genes) & uni
    rows = []
    for term, members in PROGRAMMES.items():
        present = set(members) & uni
        if not present:
            continue
        overlap = sorted(drawn & present)
        p = hypergeom.sf(len(overlap) - 1, len(uni), len(present), len(drawn))
        rows.append({"term": term,
                     "overlap": f"{len(overlap)}/{len(present)}",
                     "n_overlap": len(overlap),
                     "p_value": float(p),
                     "genes": ";".join(overlap) if overlap else "—"})
    out = pd.DataFrame(rows)
    if len(out):
        out["adjusted_p"] = multipletests(out["p_value"], method="fdr_bh")[1]
        out = out.sort_values("p_value")
    return out


def enrichr(genes):
    """Open-ended enrichment; returns None when the service is unreachable."""
    try:
        import gseapy as gp
        res = gp.enrichr(gene_list=list(genes), gene_sets=GENE_SETS,
                         organism="human", outdir=None).results
    except Exception as exc:
        print(f"    Enrichr unavailable ({type(exc).__name__})")
        return None
    out = pd.DataFrame({
        "gene_set": res["Gene_set"], "term": res["Term"],
        "overlap": res["Overlap"], "p_value": res["P-value"],
        "adjusted_p": res["Adjusted P-value"], "genes": res["Genes"],
    })
    # Enrichr returns one row per queried library; identical terms recur.
    out = (out.drop_duplicates(subset=["term", "overlap"])
              .sort_values("p_value").reset_index(drop=True))
    return out


def main():
    ranking = pd.read_csv(f"{C.TAB}/shap_feature_ranking.csv")
    deg = pd.read_csv(f"{C.TAB}/deg_all_arms.csv")
    universe = sorted({s for s in C.symbols().values
                       if isinstance(s, str) and s and not s.startswith("ENSG")})

    targeted_frames, deg_frames, open_frames = [], [], []

    for arm in C.ARMS:
        panel = ranking[ranking.arm == arm].nsmallest(TOP_N, "rank")
        genes = [g for g in panel["gene_symbol"].unique()
                 if isinstance(g, str) and not g.startswith("ENSG")]
        print(f"\n=== {C.ARM_LABEL[arm]} ===")
        print(f"  A. targeted test of {len(genes)} SHAP-ranked genes")
        t = targeted(genes, universe)
        if len(t):
            t.insert(0, "arm_label", C.ARM_LABEL[arm])
            t.insert(0, "arm", arm)
            targeted_frames.append(t)
            print(t[["term", "overlap", "p_value", "adjusted_p"]].to_string(index=False))

        sig = deg[(deg.arm == arm) & (deg.fdr < 0.05)].dropna(subset=["gene_symbol"])
        sig = sig[~sig["gene_symbol"].astype(str).str.startswith("ENSG")]
        print(f"  B. genes at FDR < 0.05: {len(sig):,}")
        if len(sig) >= 20:
            top = sig.nsmallest(MAX_DEG, "p_value")["gene_symbol"].unique()
            e = enrichr(top)
            if e is not None and len(e):
                e = e.head(20)
                e.insert(0, "arm_label", C.ARM_LABEL[arm])
                e.insert(0, "arm", arm)
                deg_frames.append(e)
                print(e[["term", "overlap", "adjusted_p"]].head(10).to_string(index=False))

        print("  C. open-ended enrichment on the SHAP panel")
        o = enrichr(genes)
        if o is not None and len(o):
            o = o.head(15)
            o.insert(0, "arm_label", C.ARM_LABEL[arm])
            o.insert(0, "arm", arm)
            open_frames.append(o)

    if targeted_frames:
        pd.concat(targeted_frames, ignore_index=True).to_csv(
            f"{C.TAB}/enrichment_targeted.csv", index=False)
    if deg_frames:
        pd.concat(deg_frames, ignore_index=True).to_csv(
            f"{C.TAB}/enrichment_deg.csv", index=False)
    if open_frames:
        pd.concat(open_frames, ignore_index=True).to_csv(
            f"{C.TAB}/enrichment_shap_open.csv", index=False)
    else:
        pd.DataFrame(columns=["arm", "arm_label", "gene_set", "term", "overlap",
                              "p_value", "adjusted_p", "genes"]).to_csv(
            f"{C.TAB}/enrichment_shap_open.csv", index=False)
    print("\nwrote enrichment_targeted.csv, enrichment_deg.csv, "
          "enrichment_shap_open.csv")


if __name__ == "__main__":
    main()
