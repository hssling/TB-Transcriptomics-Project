# -*- coding: utf-8 -*-
"""Write the submission-package manifest."""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TAB = f"{HERE}/tables2"
OUT = f"{HERE}/deliverables/SUBMISSION_PACKAGE.md"

M = json.load(open(f"{TAB}/arm_metrics.json"))
degs = pd.read_csv(f"{TAB}/deg_summary.csv")
ext = pd.read_csv(f"{TAB}/external_transfer_auc.csv")


def best(arm):
    return M[arm]["models"][M[arm]["best_model"]]


def line(arm):
    b = best(arm)
    lo, hi = b["roc_auc_ci"]
    p = M[arm]["permutation"]["permutation_p"]
    fdr = int(degs[degs.arm == arm].iloc[0].fdr_significant)
    return (f"| {ARM_LABEL[arm]} | {M[arm]['n']} | {M[arm]['n_events']} | "
            f"{b['roc_auc']:.2f} ({lo:.2f}–{hi:.2f}) | {b['pr_auc']:.2f} | "
            f"{p:.3f} | {fdr:,} |")


ARM_LABEL = {"DX": "Pre-treatment", "day_7": "Day 7", "week_4": "Week 4",
             "week_24": "Week 24", "combined": "All timepoints"}

files = [
    ("TB_Treatment_Outcome_DAI_Revision_v14.docx", "Revised manuscript"),
    ("Response_to_Reviewers_DAI_Revision_v14.docx",
     "Point-by-point response, in table form"),
    ("Cover_Letter_DAI_Revision_v14.docx", "Cover letter"),
    ("Supplementary_Material_DAI_Revision_v14.docx",
     "Supplementary tables S1–S14 and figure S1"),
    ("figures/", "Main figures at 300 dpi"),
    ("tables/", "Machine-readable result tables"),
]

lines = [
    "# Submission package",
    "",
    "Manuscript: *Whole-blood transcriptomic signatures of unfavourable "
    "tuberculosis treatment outcome before and during therapy: an exploratory "
    "machine-learning and immune-deconvolution study*",
    "",
    "## Files",
    "",
    "| File | Contents |",
    "| --- | --- |",
]
lines += [f"| `{f}` | {d} |" for f, d in files]

lines += [
    "",
    "## Headline results",
    "",
    "| Arm | n | Events | ROC-AUC (95% CI) | PR-AUC | Permutation p | Genes at FDR < 0.05 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
lines += [line(a) for a in ["DX", "day_7", "week_4", "week_24"]]

lines += [
    "",
    f"Independent cohort (GSE67589): signature transfer ROC-AUC "
    f"{ext.roc_auc.min():.2f}–{ext.roc_auc.max():.2f}, every confidence "
    "interval spanning 0.5. The signature did not generalise, and the "
    "manuscript reports this as a negative result.",
    "",
    "## Reproducing the analysis",
    "",
    "```",
    "python analysis/20_build_full_dataset.py     # rebuild from the GEO deposit",
    "python analysis/21_arm_models.py             # discrimination per arm",
    "python analysis/22_deconvolution_arms.py     # immune composition",
    "python analysis/23_shap_arms.py              # feature attribution",
    "python analysis/24_deg_arms.py               # differential expression",
    "python analysis/25_enrichment.py             # pathway over-representation",
    "python analysis/26_network_shap.py           # conditional-dependency network",
    "python analysis/27_external_gse67589.py      # independent cohort",
    "python analysis/28_flowchart.py              # study flow diagram",
    "python analysis/29_comparative.py            # performance and contrast figures",
    "python analysis/30_confounders.py            # sex and bacterial-load audit",
    "```",
    "",
    "Raw data are downloaded from the NCBI Gene Expression Omnibus on first "
    "run. Random seeds are fixed throughout.",
    "",
]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf8") as fh:
    fh.write("\n".join(lines))
print(f"wrote {OUT}")
