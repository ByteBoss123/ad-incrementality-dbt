#!/usr/bin/env bash
# Independent BigQuery path for the CUPED + decile segment analysis.
# Run from Google Cloud Shell (bq and gsutil preinstalled, project already authenticated).
#
#   bash bigquery/run_bigquery.sh <criteo-research-uplift-v2.1.csv.gz>
#
# Loads the full Criteo release into BigQuery, fits the outcome model with BigQuery ML
# (linear regression, normal equation, no regularization), then computes CUPED-adjusted
# lift and per-decile effects in SQL. Writes results/bigquery_*.json for bigquery/compare.py.
#
# Cost: ~1.8 GB stored, well inside the BigQuery free tier (10 GB storage, 1 TB queries,
# 10 GB BQML training per month). Delete the dataset afterwards with:
#   bq rm -r -f -d "$PROJECT:$DATASET"
set -euo pipefail
SRC="${1:?path to criteo-research-uplift-v2.1.csv.gz}"
PROJECT="$(gcloud config get-value project 2>/dev/null)"
DATASET="${DATASET:-criteo_uplift}"
LOCATION="${LOCATION:-US}"
BUCKET="${BUCKET:-${PROJECT}-criteo-uplift}"
cd "$(dirname "$0")/.."
mkdir -p results

echo "Project: $PROJECT  dataset: $DATASET  bucket: gs://$BUCKET"
if [ "${SKIP_LOAD:-0}" != "1" ]; then
gsutil ls -b "gs://$BUCKET" >/dev/null 2>&1 || gsutil mb -l "$LOCATION" "gs://$BUCKET"
gsutil -q cp -n "$SRC" "gs://$BUCKET/criteo-research-uplift-v2.1.csv.gz"
bq --location="$LOCATION" show "$PROJECT:$DATASET" >/dev/null 2>&1 || bq --location="$LOCATION" mk -d "$PROJECT:$DATASET"

bq load --replace --source_format=CSV --skip_leading_rows=1 "$DATASET.criteo_full" \
  "gs://$BUCKET/criteo-research-uplift-v2.1.csv.gz" \
  f0:FLOAT64,f1:FLOAT64,f2:FLOAT64,f3:FLOAT64,f4:FLOAT64,f5:FLOAT64,f6:FLOAT64,f7:FLOAT64,f8:FLOAT64,f9:FLOAT64,f10:FLOAT64,f11:FLOAT64,treatment:INT64,conversion:INT64,visit:INT64,exposure:INT64
fi

q() { bq query --use_legacy_sql=false --format=json --max_rows=1000 "$@"; }

q "SELECT COUNT(*) AS n FROM \`$DATASET.criteo_full\`" > results/bigquery_rowcount.json

for Y in visit conversion; do
  echo "== $Y"
  q "CREATE OR REPLACE MODEL \`$DATASET.covariate_$Y\`
     OPTIONS(model_type='linear_reg', input_label_cols=['$Y'], optimize_strategy='NORMAL_EQUATION',
             l2_reg=0, data_split_method='NO_SPLIT') AS
     SELECT f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11, $Y FROM \`$DATASET.criteo_full\`" >/dev/null

  q "CREATE OR REPLACE TABLE \`$DATASET.scored_$Y\` AS
     SELECT treatment, $Y AS y, predicted_$Y AS c
     FROM ML.PREDICT(MODEL \`$DATASET.covariate_$Y\`, TABLE \`$DATASET.criteo_full\`)" >/dev/null

  sed "s/{DATASET}/$DATASET/g; s/{Y}/$Y/g" bigquery/cuped.sql | q > "results/bigquery_cuped_$Y.json"
  sed "s/{DATASET}/$DATASET/g; s/{Y}/$Y/g" bigquery/segments.sql | q > "results/bigquery_segments_$Y.json"
done
echo "Done. Now run: python3 bigquery/compare.py"
