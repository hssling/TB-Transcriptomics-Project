"""WP-H: Benchmark vs prior TB treatment-outcome / multi-omic ML studies.

Addresses R1.3 (benchmark vs literature) and R3.1 (the 'first' claim is
incorrect; cite & compare PMIDs 38357663, 38380250, 38514736). Positions our
contribution honestly: baseline whole-blood cellular-deconvolution + network
interpretation, NOT a superior predictor.
"""
import pandas as pd
import common
OUT_TAB = f"{common.ROOT}/DAI_Revision_2026/tables"

rows = [
    {"Study": "This study (baseline, leakage-free)",
     "Data": "Whole-blood RNA-seq (GSE89403), baseline DX",
     "N / events": "90 / 7",
     "Approach": "Marker deconvolution + ML + GGM network (associative)",
     "Treatment-failure AUC": "0.68 (95% CI 0.38-0.89)",
     "Contribution": "Cellular-resolved, sex-confounder-audited baseline risk signal"},
    {"Study": "Thompson 2017 (PMID 29050771)",
     "Data": "Whole-blood RNA-seq (Catalysis = our source)",
     "N / events": "~70 / ~ ", "Approach": "Co-expression modules / RT-PCR signature",
     "Treatment-failure AUC": "Baseline failure signature derived; modest",
     "Contribution": "Original treatment-monitoring signatures"},
    {"Study": "Vianello/TANDEM 2022 (PMID 35precip; GSE193979)",
     "Data": "Whole-blood RNA-seq SA+Indonesia",
     "N / events": "63 / 14 poor", "Approach": "8- & 22-gene signatures",
     "Treatment-failure AUC": "0.815 (diagnosis), 0.834 (week 2)",
     "Contribution": "Good vs poor outcome at diagnosis"},
    {"Study": "RePORT-Brazil 2025 (PMID 41282706)",
     "Data": "Whole-blood transcriptomic signatures",
     "N / events": "Large cohort", "Approach": "Curated signatures, multi-timepoint",
     "Treatment-failure AUC": "<0.70 for failure (death/recurrence higher)",
     "Contribution": "Shows baseline FAILURE prediction is hard field-wide"},
    {"Study": "Sambarey 2024 (PMID 38357663)",
     "Data": "Multimodal clinical/radiological/microbiological",
     "N / events": "5060 / -", "Approach": "Random forest, 203 features",
     "Treatment-failure AUC": "~0.83 accuracy",
     "Contribution": "Personalized multimodal prognosis (not transcriptomic-cellular)"},
    {"Study": "Vinhaes 2024 (PMID 38380250)",
     "Data": "Multi-omics (cytokines, expression, eicosanoids)",
     "N / events": "76 / -", "Approach": "ML on multi-platform TB-DM",
     "Treatment-failure AUC": "n/a (characterization)",
     "Contribution": "Multi-omic TB-diabetes interaction"},
    {"Study": "Peng 2024 (PMID 38514736)",
     "Data": "Electronic medical records (TB-DM)",
     "N / events": "429 / -", "Approach": "XGBoost + SHAP + Boruta",
     "Treatment-failure AUC": "0.93",
     "Contribution": "Explainable EMR-based failure prediction (not omics)"},
]
df = pd.DataFrame(rows)
df.to_csv(f"{OUT_TAB}/wpH_benchmark_table.csv", index=False)
print(df.to_string(index=False))
print("\nSaved wpH_benchmark_table.csv")
