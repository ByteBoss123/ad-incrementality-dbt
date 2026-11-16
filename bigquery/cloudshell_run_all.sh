#!/usr/bin/env bash
# One-shot Cloud Shell runner: picks the project, downloads the official file,
# runs the DuckDB path and the BigQuery path, compares them, and serves results/
# on port 8080 (Cloud Shell web preview) so they can be read back.
#   curl -sL https://raw.githubusercontent.com/ByteBoss123/ad-incrementality-dbt/cuped-segments-bigquery/bigquery/cloudshell_run_all.sh | bash
set -uo pipefail
LOG=~/cuped_run.log
exec > >(tee -a "$LOG") 2>&1
echo "== start $(date -u)"

if [ -z "${PROJECT:-}" ]; then
  for p in $(gcloud projects list --filter='name:"My First Project"' --format='value(projectId)'); do
    billing=$(gcloud billing projects describe "$p" --format='value(billingEnabled)' 2>/dev/null)
    vertex=$(gcloud services list --enabled --project "$p" --format='value(config.name)' 2>/dev/null | grep -c aiplatform.googleapis.com)
    echo "candidate $p billing=$billing vertex=$vertex"
    if [ "$billing" = "True" ] && [ "$vertex" -gt 0 ]; then PROJECT=$p; break; fi
  done
fi
if [ -z "${PROJECT:-}" ]; then echo "NO_PROJECT_FOUND"; exit 1; fi
echo "PROJECT=$PROJECT"
gcloud config set project "$PROJECT"
gcloud services enable bigquery.googleapis.com storage.googleapis.com

cd ~ && rm -rf ad-incrementality-dbt
git clone -q -b cuped-segments-bigquery https://github.com/ByteBoss123/ad-incrementality-dbt
cd ad-incrementality-dbt
pip install --user -q duckdb numpy scipy

URL=https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz
[ -s ~/criteo.csv.gz ] || curl -sL -o ~/criteo.csv.gz "$URL"
echo "sha256 $(sha256sum ~/criteo.csv.gz | cut -d' ' -f1) expected $(cut -d' ' -f1 raw/criteo_full/source_file.sha256)"

echo "== duckdb path $(date -u)"
python3 variance_reduction/cuped_segments.py ~/criteo.csv.gz --low-memory
echo "== bigquery path $(date -u)"
bash bigquery/run_bigquery.sh ~/criteo.csv.gz
echo "== compare $(date -u)"
python3 bigquery/compare.py
echo "compare_exit=$?"

cp "$LOG" results/run.log
cd results && (nohup python3 -m http.server 8080 >/dev/null 2>&1 &)
echo "ALL_DONE $(date -u)"
