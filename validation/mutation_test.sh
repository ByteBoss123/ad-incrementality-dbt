#!/usr/bin/env bash
# Proves the dbt tests catch bad data: copies the project, injects known
# defects into the raw files, and expects `dbt build` to fail on each one.
set -uo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
cp -r "$SRC"/{dbt_project.yml,profiles.yml,models,macros,tests,raw} "$TMP"/
cd "$TMP"
python3 - <<'PY'
import pandas as pd
f = "raw/criteo/predictions_visit_frac0.1_seed43.parquet"
d = pd.read_parquet(f)
s42 = pd.read_parquet("raw/criteo/predictions_visit_frac0.1_seed42.parquet")
# 1) conflicting duplicate: a seed-42 user re-appears in seed 43 with flipped treatment
dup = s42.iloc[[0]].copy(); dup["w"] = 1 - dup["w"]
# 2) invalid treatment code
bad = d.iloc[[0]].copy(); bad["row_id"] = 99; bad["w"] = 2
pd.concat([d, dup, bad]).to_parquet(f, index=False)
PY
# 3) clicks > impressions in the ads export
printf "\n1,916,103916,30-34,M,15,10,50,1.00,1,0\n" >> raw/KAG_conversion_data.csv
dbt build --profiles-dir . > build.log 2>&1
grep -E "FAIL [0-9]+ " build.log | sed 's/\x1b\[[0-9;]*m//g' | awk '{$1="";print}' | sort -u
grep -E "Done\." build.log | sed 's/\x1b\[[0-9;]*m//g'
rm -rf "$TMP"
