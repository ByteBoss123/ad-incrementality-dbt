#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
bash fetch_data.sh
dbt build --profiles-dir .
python validation/validate.py
python -m pytest -q sigma/tests
python validation/snowflake_dialect_check.py
