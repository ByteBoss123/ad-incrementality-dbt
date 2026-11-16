# Running the CUPED + segment analysis (Google Cloud Shell)

Both paths need the 12 pre-treatment features (f0..f11), which the committed
`raw/criteo_full` parquet does not include, so they read the official file directly.

Open Cloud Shell (shell.cloud.google.com) with your project selected, then:

```bash
git clone https://github.com/ByteBoss123/ad-incrementality-dbt
cd ad-incrementality-dbt
git checkout cuped-segments-bigquery
pip install --user duckdb numpy scipy

# 1. Official file (311 MB). The checksum must match raw/criteo_full/source_file.sha256
curl -L -o criteo.csv.gz \
  https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz
sha256sum criteo.csv.gz
cat raw/criteo_full/source_file.sha256

# 2. Reference path (DuckDB + numpy). --low-memory streams from the gzip
python3 variance_reduction/cuped_segments.py criteo.csv.gz --low-memory

# 3. BigQuery path (BigQuery ML outcome model + SQL)
bash bigquery/run_bigquery.sh criteo.csv.gz

# 4. Cross-check the two paths
python3 bigquery/compare.py
```

Then send back the `results/` folder (variance_reduction.json and the bigquery_*.json files).

Clean up afterwards so nothing stays billed:

```bash
bq rm -r -f -d "$(gcloud config get-value project):criteo_uplift"
gsutil rm -r "gs://$(gcloud config get-value project)-criteo-uplift"
```

Tests (synthetic planted-effect data, used only to test the code):
`cd variance_reduction && python3 -m pytest -q`
