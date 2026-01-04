
import os
import glob
import shutil

paths = [
    "outputs/metadata/geo_samples.parquet",
    "outputs/metadata/cohorts.parquet",
    "outputs/dataset",
    "outputs/models"
]

for p in paths:
    if os.path.exists(p):
        if os.path.isfile(p):
            os.remove(p)
            print(f"Removed file: {p}")
        elif os.path.isdir(p):
            shutil.rmtree(p)
            print(f"Removed dir: {p}")
            
print("Cleanup complete.")
