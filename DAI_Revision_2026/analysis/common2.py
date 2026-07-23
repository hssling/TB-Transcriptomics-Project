"""Shared substrate for the three-arm analysis of GSE89403.

Arms
  DX       pre-treatment (diagnosis) - intrinsic patient biology
  day_7    early on-treatment
  week_4   intensive-phase end
  week_24  end of therapy
  combined all timepoints, subject-grouped, for cross-state contrast only

Every arm draws on one preprocessing pass (20_build_full_dataset.py), so
differences between arms reflect biology rather than pipeline variation.
"""
import os

import env_fix  # noqa: F401  (must precede scikit-learn)

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA = f"{ROOT}/data2"
TAB = f"{ROOT}/tables2"
FIG = f"{ROOT}/figures2"
os.makedirs(TAB, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

ARMS = ["DX", "day_7", "week_4", "week_24"]
ARM_LABEL = {
    "DX": "Pre-treatment",
    "day_7": "Day 7",
    "week_4": "Week 4",
    "week_24": "Week 24",
    "combined": "All timepoints",
}
SEED = 20260723

# Canonical immune marker panels (HGNC symbols).
MARKERS = {
    "Neutrophil": ["FCGR3B", "CSF3R", "CXCR2", "CXCR1", "S100A8", "S100A9",
                   "S100A12", "MPO", "ELANE", "FUT4", "CEACAM3", "FFAR2",
                   "PROK2", "MMP8", "MMP9", "DEFA1", "DEFA3", "DEFA4",
                   "LCN2", "CAMP", "LTF", "BPI"],
    "T_cell": ["CD3D", "CD3E", "CD3G", "CD2", "CD28", "IL7R", "CD8A", "CD8B",
               "LCK", "TRAC", "TRBC2", "CCR7", "CD27", "CD5", "ITK", "TCF7"],
    "Monocyte": ["CD14", "LYZ", "CSF1R", "FCN1", "VCAN", "CD68", "ITGAM"],
    "B_cell": ["CD19", "MS4A1", "CD79A", "CD79B", "IGHM", "BANK1", "TCL1A"],
    "NK_cell": ["NCAM1", "KLRD1", "NKG7", "GNLY", "KLRF1", "NCR1", "PRF1"],
}

_cache = {}


def _load():
    if "expr" not in _cache:
        expr = pd.read_parquet(f"{DATA}/expr_log2cpm.parquet")
        samples = pd.read_csv(f"{DATA}/samples.csv")
        samples["subject"] = samples["subject"].astype(str)
        genes = pd.read_csv(f"{DATA}/genes.csv")
        _cache["expr"] = expr
        _cache["samples"] = samples.set_index("sample_code")
        _cache["genes"] = genes.set_index("ensembl")["symbol"]
    return _cache["expr"], _cache["samples"], _cache["genes"]


def load_arm(arm):
    """Return (X, y, meta) for one arm. X is samples x genes."""
    expr, samples, _ = _load()
    if arm == "combined":
        meta = samples.copy()
    else:
        meta = samples[samples["time"] == arm].copy()
    ids = [s for s in meta.index if s in expr.columns]
    meta = meta.loc[ids]
    X = expr[ids].T.astype(float)
    y = meta["label"].astype(int)
    return X, y, meta


def symbols():
    """Ensembl id -> HGNC symbol."""
    return _load()[2]


def symbol_to_ensembl():
    s = symbols()
    out = {}
    for ens, sym in s.items():
        if isinstance(sym, str) and sym:
            out.setdefault(sym, []).append(ens)
    return out


def to_symbols(ensembl_ids):
    s = symbols()
    return [s.get(g, g) if isinstance(s.get(g), str) else g for g in ensembl_ids]


def celltype_scores(X):
    """Marker-gene-set z-score enrichment per sample."""
    s2e = symbol_to_ensembl()
    Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)
    out, used = {}, {}
    for cell, genes in MARKERS.items():
        cols = []
        for g in genes:
            cols.extend(s2e.get(g, []))
        cols = [c for c in cols if c in Xz.columns]
        used[cell] = len(cols)
        out[cell] = Xz[cols].mean(1) if cols else pd.Series(np.nan, index=Xz.index)
    S = pd.DataFrame(out)
    S["NLR_score"] = S["Neutrophil"] - S["T_cell"]
    return S, used


def rank_biserial(group1, group0):
    """Rank-biserial correlation with its Mann-Whitney U test."""
    from scipy.stats import mannwhitneyu
    u, p = mannwhitneyu(group1, group0, alternative="two-sided")
    r = 2 * u / (len(group1) * len(group0)) - 1
    return u, p, r
