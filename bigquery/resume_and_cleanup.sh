#!/usr/bin/env bash
# Finish the BigQuery path after an interrupted Cloud Shell session (data already loaded),
# compare with the DuckDB results, delete the BigQuery dataset and bucket, and serve
# results/ on port 8080 for web preview. Run in the background:
#   nohup bash bigquery/resume_and_cleanup.sh > ~/resume.log 2>&1 &
set -uo pipefail
cd ~/ad-incrementality-dbt && git pull -q
PROJECT="$(gcloud config get-value project 2>/dev/null)"
SKIP_LOAD=1 bash bigquery/run_bigquery.sh unused
python3 bigquery/compare.py; echo "compare_exit=$?"
bq rm -r -f -d "$PROJECT:criteo_uplift" && echo "dataset deleted"
gsutil -q -m rm -r "gs://${PROJECT}-criteo-uplift" && echo "bucket deleted"
cp ~/cuped_run.log results/run.log 2>/dev/null; cp ~/resume.log results/resume.log 2>/dev/null
cd results && (nohup python3 -m http.server 8080 >/dev/null 2>&1 &)
echo "ALL_DONE $(date -u)"
