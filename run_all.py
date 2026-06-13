#!/usr/bin/env python
"""Single entry point to reproduce the full DAI TB treatment-failure analysis.

Runs every analysis step in order and then rebuilds the manuscript,
supplementary and response-letter documents. All paths are resolved relative
to this repository, so it runs anywhere after `pip install -r requirements.txt`.

Usage:
    python run_all.py            # full pipeline
    python run_all.py --analysis # analysis steps only (no document build)
Steps that require internet (gene-symbol mapping, HPA atlas, external cohort
download) degrade gracefully if offline; cached tables are reused.
"""
import os
import sys
import subprocess

REPO = os.path.abspath(os.path.dirname(__file__))
os.environ["TBREPRO_ROOT"] = REPO
ANALYSIS = os.path.join(REPO, "DAI_Revision_2026", "analysis")
BUILD = os.path.join(REPO, "DAI_Revision_2026")

ANALYSIS_STEPS = [
    "00_verify_data.py",
    "01_metric_suite.py",
    "01b_sensitivity_timepoints.py",
    "02_deg_volcano.py",
    "02b_deg_corrected.py",
    "03_shap.py",
    "04_deconvolution.py",
    "05_confounders.py",
    "06_external_validation.py",
    "07_celltype_specificity.py",
    "08_benchmark_table.py",
    "09_recheck.py",
    "10_enrichment.py",
    "11_network.py",
]
BUILD_STEPS = [
    "build_manuscript.py",
    "build_supplementary.py",
    "build_response_letter.py",
]


def run(script, cwd):
    print(f"\n{'='*70}\n>>> {script}\n{'='*70}", flush=True)
    r = subprocess.run([sys.executable, script], cwd=cwd, env=os.environ)
    if r.returncode != 0:
        print(f"!! {script} exited with code {r.returncode}", flush=True)
    return r.returncode


def main():
    analysis_only = "--analysis" in sys.argv
    for s in ANALYSIS_STEPS:
        run(s, ANALYSIS)
    if not analysis_only:
        for s in BUILD_STEPS:
            run(s, BUILD)
    print("\nDone. Outputs in DAI_Revision_2026/{tables,figures,deliverables}.")


if __name__ == "__main__":
    main()
