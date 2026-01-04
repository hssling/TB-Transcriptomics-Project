import pandas as pd
import numpy as np
import GEOparse
import os
import requests
import gzip
from pathlib import Path

mode = snakemake.config.get("ingestion_mode", "processed")
cohorts = pd.read_parquet(snakemake.input["cohorts"])
gse_list = sorted(cohorts["cohort_id"].unique().tolist())
Path("outputs/expression").mkdir(parents=True, exist_ok=True)

def _extract_gsm_tables(g):
    gsm_tables = []
    # Check if g is valid
    if not g or not hasattr(g, 'gsms'):
        return []
    for gsm_name, gsm in g.gsms.items():
        if gsm.table is None or gsm.table.empty:
            continue
        tbl = gsm.table.copy()
        gene_col = tbl.columns[0]
        val_cols = [c for c in tbl.columns if c != gene_col]
        expr_col = None
        for c in val_cols:
            if pd.api.types.is_numeric_dtype(tbl[c]):
                expr_col = c
                break
        if expr_col is None and val_cols:
            expr_col = val_cols[0]
        if expr_col is None:
            continue
        out = tbl[[gene_col, expr_col]].rename(columns={gene_col:"gene_id", expr_col:gsm_name})
        gsm_tables.append(out)
    return gsm_tables

def download_file(url, out_path, timeout=120):
    if url.startswith("ftp://"):
        url = url.replace("ftp://", "https://")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} to {out_path}...")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
    return out_path

def ingest_processed():
    matrices = []
    for gse in gse_list:
        gsm_tables = []
        g = None
        
        # 1. SPECIAL CASE: Look for local high-quality supplementary files FIRST
        # Prioritize gene-level expression over junction counts
        print(f"Scanning local text/csv files for {gse}...")
        all_candidates = [f for f in os.listdir("outputs/expression") if gse in f and f.endswith(".gz") and "series_matrix" not in f]
        
        # Filter and prioritize: gene expression > counts > junction
        gene_files = [f for f in all_candidates if "gene" in f.lower() and "junc" not in f.lower()]
        count_files = [f for f in all_candidates if "count" in f.lower() and "junc" not in f.lower() and f not in gene_files]
        other_files = [f for f in all_candidates if f not in gene_files and f not in count_files and "junc" not in f.lower()]
        
        # Prioritize: gene files first, then counts, then others, skip junction files
        local_candidates = gene_files + count_files + other_files
        
        for cand in local_candidates:
            p = os.path.join("outputs/expression", cand)
            print(f"Attempting to parse local candidate: {cand}")
            try:
                sep = "\t" if ".txt" in cand or ".tab" in cand or ".tsv" in cand else ","
                if "csv" in cand: sep = ","
                df = pd.read_csv(p, sep=sep, index_col=0) # Index usually Gene ID or first col
                # If first row contains strings (e.g. Gene Name), skip it?
                # GSE89403 log2 file: "ENSG...", "GeneName", val, val...
                # If first column is index, second is GeneName, then Samples.
                if df.shape[1] > 1 and not pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
                     # drop extraction metadata col if present (e.g. Gene Symbol)
                     df = df.iloc[:, 1:]
                
                # Rename columns from sample titles to GSM IDs
                gse_cohorts = cohorts[cohorts["cohort_id"] == gse]
                if len(gse_cohorts) > 0 and "title" in gse_cohorts.columns:
                    # Create mapping: extract prefix from title -> sample_id
                    # For GSE89403: "S100_day_7-TB Subjects..." -> "S100_day_7"
                    title_to_gsm = {}
                    for _, row in gse_cohorts.iterrows():
                        title = row["title"]
                        # Extract prefix before first "-" or use full title
                        prefix = title.split("-")[0] if "-" in title else title
                        title_to_gsm[prefix] = row["sample_id"]
                    
                    # Rename columns that match titles or prefixes
                    rename_map = {}
                    for col in df.columns:
                        if col in title_to_gsm:
                            rename_map[col] = title_to_gsm[col]
                    if rename_map:
                        df = df.rename(columns=rename_map)
                        print(f"Renamed {len(rename_map)} columns from titles to GSM IDs")
                
                # Check data quality
                if df.iloc[:, 0].apply(lambda x: isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.','').isdigit())).all() == False:
                    # Maybe header issues?
                    # Try converting to numeric
                    df = df.apply(pd.to_numeric, errors='coerce')
                
                # Check nulls
                if df.isnull().mean().mean() < 0.5:
                      df.index.name = "gene_id"
                      merged = df.reset_index()
                      matrices.append(merged)
                      print(f"Accepted {cand} ({df.shape})")
                      gsm_tables = [merged] # Mark as done
                      break
            except Exception as e:
                print(f"Failed candidate {cand}: {e}")
                
        if gsm_tables:
            continue

        # 2. Try GEOparse full SOFT
        try:
            search_dir = "outputs/metadata"
            try:
                g = GEOparse.get_GEO(geo=gse, destdir=search_dir, how="full")
                gsm_tables = _extract_gsm_tables(g)
            except Exception:
                pass # Fail silently
        except Exception:
            pass

        # 3. Fallback: Series Matrix (GEOparse or Direct)
        if not gsm_tables:
            print(f"Fallback to Series Matrix for {gse}...")
            # Try loading local Series Matrix first
            matrix_path = os.path.join("outputs/expression", f"{gse}_series_matrix.txt.gz")
            if os.path.exists(matrix_path):
                try:
                    print(f"Parsing local Series Matrix: {matrix_path}")
                    df = pd.read_csv(matrix_path, sep="\t", comment="!", index_col=0)
                    # VALIDATE IT
                    if df.empty or df.size == 0 or df.isnull().all().all():
                        print("Local Series Matrix is empty/null. Skipping.")
                    else:
                        df.index.name = "gene_id"
                        merged = df.reset_index()
                        matrices.append(merged)
                        continue # Success!
                except Exception as e:
                    print(f"Failed to parse local matrix: {e}")

            # Try GEOparse download/load
            # NOTE: GEOparse does not support how='series_matrix' directly in get_GEO
            # We rely on local file check above.
            pass

        # 4. Fallback: Supplementary File (HTTPS Download)
        if not gsm_tables:
            print(f"Checking Series Supplementary Files for {gse}...")
            fallback_success = False
            suppls = []
            if g and g.metadata.get("supplementary_file"):
                s = g.metadata["supplementary_file"]
                suppls = [s] if isinstance(s, str) else s
            
            # Prioritize gene-level files over junction counts
            gene_suppls = [url for url in suppls if "gene" in url.lower() and "junc" not in url.lower()]
            other_suppls = [url for url in suppls if url not in gene_suppls and "junc" not in url.lower()]
            junction_suppls = [url for url in suppls if "junc" in url.lower()]
            
            # Try gene files first, then others, junction files last
            prioritized_suppls = gene_suppls + other_suppls + junction_suppls
            
            for url in prioritized_suppls:
                # Check for expression data files (including Excel), skip junction files unless no alternative
                if any(x in url for x in ["rawdata", "counts", "matrix", "txt.gz", "csv.gz", ".xlsx", ".xls"]):
                    fname = os.path.basename(url)
                    local_path = os.path.join("outputs/expression", fname)
                    try:
                        if not os.path.exists(local_path):
                            download_file(url, local_path)
                        print(f"Parsing {local_path}...")
                        
                        # Handle Excel files
                        if fname.endswith('.xlsx') or fname.endswith('.xls'):
                            try:
                                # Try reading Excel file
                                df = pd.read_excel(local_path, index_col=0, engine='openpyxl' if fname.endswith('.xlsx') else None)
                                print(f"Successfully read Excel file: {fname} with shape {df.shape}")
                                
                                # Rename columns from sample titles to GSM IDs
                                # Get mapping from cohorts metadata
                                gse_cohorts = cohorts[cohorts["cohort_id"] == gse]
                                if len(gse_cohorts) > 0 and "title" in gse_cohorts.columns:
                                    # Create mapping: title -> sample_id
                                    title_to_gsm = dict(zip(gse_cohorts["title"], gse_cohorts["sample_id"]))
                                    # Rename columns that match titles
                                    rename_map = {}
                                    for col in df.columns:
                                        if col in title_to_gsm:
                                            rename_map[col] = title_to_gsm[col]
                                    if rename_map:
                                        df = df.rename(columns=rename_map)
                                        print(f"Renamed {len(rename_map)} columns from titles to GSM IDs")
                            except Exception as excel_error:
                                print(f"Failed to read as Excel: {excel_error}")
                                continue
                        else:
                            # Handle text files (CSV, TSV, etc.)
                            sep = "\t" if ".txt" in fname or ".tab" in fname or ".tsv" in fname else ","
                            if "csv" in fname: sep = ","
                            df = pd.read_csv(local_path, sep=sep, index_col=0)
                        
                        # Data Cleaning (similar to candidate logic)
                        if df.shape[1] > 1 and not pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
                             df = df.iloc[:, 1:]
                        df = df.apply(pd.to_numeric, errors='coerce')

                        if df.isnull().mean().mean() < 0.5:
                            df.index.name = "gene_id"
                            merged = df.reset_index()
                            matrices.append(merged)
                            fallback_success = True
                            print(f"Successfully loaded {fname}")
                            break
                    except Exception as e:
                        print(f"Failed to process {url}: {e}")
            
            if fallback_success:
                continue

            raise RuntimeError(f"No valid data found for {gse}. Check log.")
            
        if gsm_tables and not isinstance(gsm_tables[0], pd.DataFrame): # it is list of df
             merged = gsm_tables[0]
             for t in gsm_tables[1:]:
                 merged = merged.merge(t, on="gene_id", how="outer")
             matrices.append(merged)

    # Merge all GSEs (inner merge to keep only common genes)
    print("Merging cohorts...")
    expr = matrices[0]
    for m in matrices[1:]:
        print(f"Merging with next matrix ({m.shape})...")
        expr = expr.merge(m, on="gene_id", how="inner")  # Changed to inner to keep only common genes

    keep = set(cohorts["sample_id"].tolist())
    keep.add("gene_id")
    cols = [c for c in expr.columns if c in keep]
    expr = expr[cols]
    return expr

def ingest_raw_fastq_placeholder():
    raise RuntimeError("raw_fastq mode requires Salmon rulechain.")

expr = ingest_processed() if mode == "processed" else ingest_raw_fastq_placeholder()
expr.to_parquet(snakemake.output[0], index=False)
print(f"Ingested expression matrix {expr.shape} → {snakemake.output[0]}")
