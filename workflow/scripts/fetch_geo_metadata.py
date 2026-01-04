import pandas as pd
import GEOparse
from pathlib import Path

gse_list = snakemake.config.get("geo_series", [])
rows = []

Path("outputs/metadata").mkdir(parents=True, exist_ok=True)

for gse in gse_list:
    g = GEOparse.get_GEO(geo=gse, destdir="outputs/metadata", how="full")
    for gsm_name, gsm in g.gsms.items():
        meta = {"cohort_id": gse, "sample_id": gsm_name}
        meta["title"] = gsm.metadata.get("title", [""])[0]
        chars = gsm.metadata.get("characteristics_ch1", [])
        meta["characteristics"] = " | ".join(chars) if isinstance(chars, list) else str(chars)
        rel = gsm.metadata.get("relation", [])
        meta["relation"] = " | ".join(rel) if isinstance(rel, list) else str(rel)
        sup = gsm.metadata.get("supplementary_file", [])
        meta["supplementary_file"] = " | ".join(sup) if isinstance(sup, list) else str(sup)
        rows.append(meta)

df = pd.DataFrame(rows)
df.to_parquet(snakemake.output[0], index=False)
print(f"Wrote GEO GSM metadata for {len(df)} samples → {snakemake.output[0]}")
