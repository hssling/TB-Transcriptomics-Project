"""Rebuild the complete GSE89403 analysis substrate from the primary GEO deposit.

The earlier working matrix held only a lane-level subset (254 arrays, 127
biological samples) in which unfavourable-outcome subjects were represented at
diagnosis alone. The full deposit contains 453 lane-merged libraries covering
all four protocol timepoints for every subject, which supports a pre-treatment
arm, a post-treatment arm and a cross-timepoint contrast on identical
preprocessing.

Outputs (DAI_Revision_2026/data2/):
  expr_log2cpm.parquet   genes x samples, log2(CPM+1)
  samples.csv            per-sample metadata with outcome label
  genes.csv              Ensembl id -> HGNC symbol
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
EXT = f"{ROOT}/external"
OUT = f"{ROOT}/data2"
os.makedirs(OUT, exist_ok=True)

COUNTS = f"{EXT}/GSE89403_rawCounts_GeneNames_AllSamples.csv.gz"
META = f"{EXT}/GSE89403_full_metadata.csv"

# Timepoint labels as deposited, ordered by protocol week.
TIMEPOINTS = ["DX", "day_7", "week_4", "week_24"]
CURE_STATES = {"Definite Cure", "Probable Cure", "Possible Cure"}
FAILURE_STATE = "Not Cured"


def load_metadata():
    md = pd.read_csv(META).drop_duplicates("sample_code")
    md = md[md["disease state"] == "TB Subjects"].copy()
    md = md[md["time"].isin(TIMEPOINTS)]

    def outcome(v):
        if v == FAILURE_STATE:
            return 1
        if v in CURE_STATES:
            return 0
        return np.nan

    md["label"] = md["treatmentresult"].map(outcome)
    md = md.dropna(subset=["label"])
    md["label"] = md["label"].astype(int)
    md["subject"] = md["subject"].astype(str)
    for c in ["mgit", "xpert", "tgrv"]:
        md[c] = pd.to_numeric(md[c], errors="coerce")
    return md.set_index("sample_code")


def load_counts(sample_codes):
    raw = pd.read_csv(COUNTS, index_col=0)
    symbols = raw["symbol"]
    keep = [c for c in sample_codes if c in raw.columns]
    counts = raw[keep].astype(float)
    return counts, symbols.loc[counts.index]


def main():
    md = load_metadata()
    counts, symbols = load_counts(list(md.index))
    md = md.loc[counts.columns]

    # Expression filter: retain genes detected in at least 10% of libraries.
    detected = (counts > 0).mean(axis=1)
    counts = counts[detected >= 0.10]
    symbols = symbols.loc[counts.index]

    # Library-size normalisation to counts per million, then log2(x+1).
    lib = counts.sum(axis=0)
    cpm = counts.div(lib, axis=1) * 1e6
    expr = np.log2(cpm + 1.0)

    expr.to_parquet(f"{OUT}/expr_log2cpm.parquet")
    md.index.name = "sample_code"
    md.reset_index().to_csv(f"{OUT}/samples.csv", index=False)
    pd.DataFrame({"ensembl": symbols.index,
                  "symbol": symbols.values}).to_csv(f"{OUT}/genes.csv",
                                                    index=False)

    print(f"genes retained : {expr.shape[0]:,} of {detected.shape[0]:,}")
    print(f"libraries      : {expr.shape[1]}")
    print(f"subjects       : {md['subject'].nunique()}")
    print("\nsamples per arm (0 = cured, 1 = unfavourable):")
    print(pd.crosstab(md["time"], md["label"]).loc[TIMEPOINTS])
    print("\nsubjects with an unfavourable outcome and a sample at each timepoint:")
    fail = md[md["label"] == 1]
    print(pd.crosstab(fail["subject"], fail["time"]))
    print(f"\nmedian library size: {lib.median():,.0f}")


if __name__ == "__main__":
    main()
