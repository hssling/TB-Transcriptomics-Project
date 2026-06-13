"""Shared data-prep for the DAI revision reanalysis.

Defines the leakage-free BASELINE cohort: GSE89403 pre-treatment (DX)
whole-blood samples, one per subject, outcome = Not Cured (failure) vs
all Cure categories. This is the honest substrate for baseline
risk-stratification (addresses R1.9, R2.10, timepoint-leakage concerns).
"""
import os
import re
import numpy as np
import pandas as pd

# Portable root resolution: env override, else two levels up from this file
# (DAI_Revision_2026/analysis/common.py -> repo root containing outputs/).
ROOT = os.environ.get(
    "TBREPRO_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def _parse(s, k):
    if not isinstance(s, str):
        return None
    m = re.search(rf"{k}:\s*([^|]+)", s)
    return m.group(1).strip() if m else None


def load_baseline():
    """Return (X, y, meta_dx) for DX-only baseline samples.

    X: DataFrame [n_samples x n_genes], index=sample_id
    y: Series of 0/1 (1 = Not Cured / failure)
    meta_dx: per-sample metadata incl. subject, bacterial-load proxies
    """
    feat = pd.read_parquet(f"{ROOT}/outputs/dataset/feature_matrix.parquet")
    labels = pd.read_parquet(f"{ROOT}/outputs/dataset/labels.parquet")
    meta = pd.read_parquet(f"{ROOT}/outputs/dataset/metadata.parquet")

    for k in ["time", "subject", "treatmentresult", "mgit", "xpert",
              "tgrv", "timetonegativity"]:
        meta[k] = meta["characteristics"].apply(lambda s: _parse(s, k))

    lab = dict(zip(labels["sample_id"], labels["label"]))
    meta["label"] = meta["sample_id"].map(lab)

    dx_ids = meta.loc[meta["time"] == "DX", "sample_id"]
    feat_dx = feat[feat["sample_id"].isin(set(dx_ids))].copy()
    feat_dx = feat_dx.drop_duplicates("sample_id").set_index("sample_id")
    meta_dx = (meta[meta["sample_id"].isin(set(feat_dx.index))]
               .drop_duplicates("sample_id").set_index("sample_id"))
    meta_dx = meta_dx.loc[feat_dx.index]

    gene_cols = [c for c in feat_dx.columns if c.startswith("ENSG")]
    X = feat_dx[gene_cols].astype(float)
    y = meta_dx["label"].astype(int)
    return X, y, meta_dx


def load_all_timepoints():
    """All 254 modeling samples with subject IDs for grouped sensitivity CV."""
    feat = pd.read_parquet(f"{ROOT}/outputs/dataset/feature_matrix.parquet")
    labels = pd.read_parquet(f"{ROOT}/outputs/dataset/labels.parquet")
    meta = pd.read_parquet(f"{ROOT}/outputs/dataset/metadata.parquet")
    for k in ["time", "subject", "treatmentresult"]:
        meta[k] = meta["characteristics"].apply(lambda s: _parse(s, k))
    lab = dict(zip(labels["sample_id"], labels["label"]))
    feat = feat.drop_duplicates("sample_id").set_index("sample_id")
    meta = meta.drop_duplicates("sample_id").set_index("sample_id")
    common = feat.index.intersection(meta.index)
    feat, meta = feat.loc[common], meta.loc[common]
    gene_cols = [c for c in feat.columns if c.startswith("ENSG")]
    X = feat[gene_cols].astype(float)
    y = meta["label"].map(lab).astype(int) if "label" not in meta else None
    y = pd.Series([lab.get(i, 0) for i in feat.index], index=feat.index).astype(int)
    return X, y, meta


# ---- gene symbol mapping (cached) ----
_SYMBOL_CACHE = f"{ROOT}/DAI_Revision_2026/tables/ensembl_symbol_map.csv"


def map_symbols(ensembl_ids):
    """Map Ensembl gene IDs to HGNC symbols, with on-disk cache + mygene."""
    import os
    cache = {}
    if os.path.exists(_SYMBOL_CACHE):
        cm = pd.read_csv(_SYMBOL_CACHE)
        cache = dict(zip(cm["ensembl"], cm["symbol"]))
    missing = [g for g in ensembl_ids if g not in cache]
    if missing:
        try:
            import mygene
            mg = mygene.MyGeneInfo()
            res = mg.querymany(missing, scopes="ensembl.gene",
                               fields="symbol", species="human",
                               verbose=False, as_dataframe=True)
            for gid, row in res.iterrows():
                sym = row.get("symbol")
                cache[gid] = sym if isinstance(sym, str) else gid
        except Exception as e:
            print("mygene mapping failed:", e)
        for g in missing:
            cache.setdefault(g, g)
        pd.DataFrame({"ensembl": list(cache.keys()),
                      "symbol": list(cache.values())}).to_csv(
            _SYMBOL_CACHE, index=False)
    return {g: cache.get(g, g) for g in ensembl_ids}


if __name__ == "__main__":
    X, y, m = load_baseline()
    print("Baseline X:", X.shape, "| failures:", int(y.sum()),
          "| cures:", int((y == 0).sum()))
    print("bacterial-load proxies non-null:",
          {c: int(m[c].replace('NA', np.nan).notna().sum())
           for c in ["mgit", "xpert", "tgrv"]})
