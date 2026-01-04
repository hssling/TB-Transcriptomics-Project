import os
import sys
import yaml
import builtins
from pathlib import Path

# Load config
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

# Load label rules path relative to config
config["label_rules_yaml"] = config.get("label_rules_yaml", "config/label_rules.yaml")

class NamedList(list):
    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self.__dict__:
                return self.__dict__[key]
            # Fallback if we want to handle failures gracefully or let it error
            raise IndexError(f"NamedList index must be integer or slice, not str '{key}' (unless valid attribute)")
        return super().__getitem__(key)


class MockSnakemake:
    def __init__(self, input=None, output=None, config=None, params=None):
        self.input = self._create_named_list(input)
        self.output = self._create_named_list(output)
        self.config = config or {}
        self.params = self._create_named_list(params)

    def _create_named_list(self, obj):
        if isinstance(obj, list):
            return NamedList(obj)
        if isinstance(obj, dict):
            # Separate integer keys (positional) from string keys (named)
            indexed = {k: v for k, v in obj.items() if isinstance(k, int)}
            named = {k: v for k, v in obj.items() if isinstance(k, str)}
            # Create list from indexed items sorted by key
            # If no indexed items, but we want to allow list access if logical, 
            # we might default to values? No, snakemake creates list from all items effectively?
            # Actually snakemake .input is a list of ALL inputs, and named ones are also attributes.
            # So let's make the list contain all values, but order might matter for scripts using [0].
            # For this mock, I provided explicit 0 keys.
            data = [v for k, v in sorted(indexed.items())]
            nl = NamedList(data)
            nl.__dict__.update(named)
            return nl
        return NamedList([])

def run_step(script_name, input_dict=None, output_dict=None, params_dict=None):
    # Check if all outputs exist (Skipping logic)
    if output_dict:
        outputs = list(output_dict.values())
        if all(os.path.exists(f) for f in outputs):
            print(f"Skipping {script_name} (outputs exist)")
            return

    print(f"\n{'='*40}\nRunning {script_name}...\n{'='*40}")
    
    # Flatten inputs/outputs for the list part of NamedList
    input_list = list(input_dict.values()) if input_dict else []
    output_list = list(output_dict.values()) if output_dict else []
    
    # Create mock snakemake
    mock = MockSnakemake(input=input_dict, output=output_list, config=config, params=params_dict)
    
    # Inject into global namespace
    builtins.snakemake = mock
    
    # Read and exec script
    script_path = Path(f"workflow/scripts/{script_name}")
    with open(script_path) as f:
        code = compile(f.read(), script_path, 'exec')
        exec(code, {'snakemake': mock})

def main():
    # 1. Fetch Metadata
    run_step(
        "fetch_geo_metadata.py",
        input_dict={},
        output_dict={0: "outputs/metadata/geo_samples.parquet"}
    )
    
    # 2. Build Cohorts Table
    run_step(
        "build_cohorts_table.py",
        input_dict={0: "outputs/metadata/geo_samples.parquet", "rules_yaml": config["label_rules_yaml"]},
        output_dict={0: "outputs/metadata/cohorts.parquet"}
    )
    
    # 3. Ingest Expression
    run_step(
        "ingest_expression.py",
        input_dict={"cohorts": "outputs/metadata/cohorts.parquet"},
        output_dict={0: "outputs/expression/expression_matrix.parquet"}
    )
    
    # 4. Build Dataset
    run_step(
        "build_dataset.py",
        input_dict={"expr": "outputs/expression/expression_matrix.parquet", "cohorts": "outputs/metadata/cohorts.parquet"},
        output_dict={
            0: "outputs/dataset/feature_matrix.parquet",
            1: "outputs/dataset/labels.parquet",
            2: "outputs/dataset/metadata.parquet"
        }
    )
    
    # 5. Train Models (Nested CV)
    run_step(
        "train_models.py",
        input_dict={
            "X": "outputs/dataset/feature_matrix.parquet",
            "y": "outputs/dataset/labels.parquet",
            "meta": "outputs/dataset/metadata.parquet"
        },
        output_dict={
            0: "outputs/models/nested_cv_metrics.json",
            1: "outputs/models/model_bundle.joblib"
        }
    )
    
    # 6. External Validation
    run_step(
        "external_validation.py",
        input_dict={
            "X": "outputs/dataset/feature_matrix.parquet",
            "y": "outputs/dataset/labels.parquet",
            "meta": "outputs/dataset/metadata.parquet",
            "bundle": "outputs/models/model_bundle.joblib"
        },
        output_dict={
            0: "outputs/models/external_validation_metrics.json",
            1: "reports/figures/roc_external_validation.png",
            2: "reports/figures/calibration_external_validation.png"
        }
    )
    
    # 7. Interpretation (SHAP & Enrichr)
    run_step(
        "interpret.py",
        input_dict={
            "X": "outputs/dataset/feature_matrix.parquet",
            "y": "outputs/dataset/labels.parquet",
            "meta": "outputs/dataset/metadata.parquet",
            "bundle": "outputs/models/model_bundle.joblib",
            "ext": "outputs/models/external_validation_metrics.json"
        },
        output_dict={
            0: "reports/figures/shap_summary.png",
            1: "reports/tables/top_features.csv",
            2: "reports/tables/enrichr_top_terms.csv"
        }
    )
    
    # 8. Render Manuscript
    run_step(
        "render_manuscript.py",
        input_dict={
            "ext": "outputs/models/external_validation_metrics.json",
            "cv": "outputs/models/nested_cv_metrics.json",
            "top": "reports/tables/top_features.csv",
            "enrich": "reports/tables/enrichr_top_terms.csv"
        },
        output_dict={0: "reports/manuscript/paper.qmd"}
    )
    
    print("\n[SUCCESS] End-to-end pipeline completed successfully!")

if __name__ == "__main__":
    main()
