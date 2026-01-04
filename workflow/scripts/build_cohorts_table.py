import pandas as pd
import re
import yaml

geo = pd.read_parquet(snakemake.input[0])
with open(snakemake.input["rules_yaml"], "r", encoding="utf-8") as f:
    rules = yaml.safe_load(f)

def apply_rules(blob, rule_list):
    for r in rule_list or []:
        if re.search(r["match"], blob):
            return r["value"]
    return None

rows = []
for _, r in geo.iterrows():
    cohort = r["cohort_id"]
    blob = " || ".join([str(r.get("title","")), str(r.get("characteristics","")), str(r.get("relation",""))])
    cohort_rules = rules.get(cohort, {})
    timepoint = apply_rules(blob, cohort_rules.get("timepoint_rules"))
    label = apply_rules(blob, cohort_rules.get("label_rules"))

    run = None
    m = re.search(r"(SRR\d+|ERR\d+|DRR\d+)", str(r.get("relation","")))
    if m:
        run = m.group(1)

    rows.append({
        "cohort_id": cohort,
        "sample_id": r["sample_id"],
        "run_accession": run,
        "platform": "rna_seq",
        "label": label,
        "timepoint": timepoint,
        "title": r.get("title",""),
        "characteristics": r.get("characteristics",""),
        "supplementary_file": r.get("supplementary_file","")
    })

cohorts = pd.DataFrame(rows)
cohorts.to_parquet(snakemake.output[0], index=False)

print("Label distribution (including None):")
print(cohorts.groupby("cohort_id")["label"].value_counts(dropna=False))
print("Timepoint distribution (including None):")
print(cohorts.groupby("cohort_id")["timepoint"].value_counts(dropna=False))
print("Run accession coverage (non-null):")
print(cohorts.groupby("cohort_id")["run_accession"].apply(lambda s: s.notna().mean()))
