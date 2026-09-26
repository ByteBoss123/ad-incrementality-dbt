#!/usr/bin/env bash
# Pulls the Criteo sample files from the public UpliftBench repo at the pinned
# commit (row positions trace to the official Criteo Uplift v2.1 file).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw/criteo
TMP="$(mktemp -d)"
git clone -q https://github.com/Aman12x/UpliftBench "$TMP/ub"
git -C "$TMP/ub" checkout -q cc85673df11cf7e869e15b9415a66fdf491870c1
cp "$TMP"/ub/results/predictions/predictions_{visit,conversion}_frac0.1_seed{42,43,44}.parquet raw/criteo/
rm -rf "$TMP"
ls -la raw/criteo
