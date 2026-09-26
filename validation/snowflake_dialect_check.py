"""Static portability check (NOT a Snowflake execution).

Parses every compiled model with sqlglot's Snowflake dialect after swapping the
DuckDB read_csv/read_parquet source reads for the RAW.* table names they would be on
Snowflake. Fails on any parse error or on DuckDB-only functions.
"""
import pathlib, re, sys
import sqlglot
from sqlglot import exp

DUCKDB_ONLY = {"read_csv", "read_csv_auto", "read_parquet", "list_value", "struct_pack"}
root = pathlib.Path("target/compiled/ad_measurement/models")
bad, n = [], 0
for f in sorted(root.rglob("*.sql")):
    sql = f.read_text()
    sql = re.sub(r"read_csv\('raw/(\w+)\.csv'[^)]*\)", r"RAW.ADS.\1", sql)
    sql = re.sub(r"read_parquet\('raw/criteo/predictions_(\w+)_frac0\.1_seed(\d+)\.parquet'\)",
                 r"RAW.CRITEO.\1_SEED\2", sql)
    sql = re.sub(r'"ad_measurement"\."main(_\w+)?"\.', "", sql)
    try:
        tree = sqlglot.parse_one(sql, read="snowflake")
        funcs = {fn.sql_name().lower() for fn in tree.find_all(exp.Func)}
        anon = {a.name.lower() for a in tree.find_all(exp.Anonymous)}
        hit = (funcs | anon) & DUCKDB_ONLY
        if hit:
            bad.append(f"{f.name}: duckdb-only {hit}")
        n += 1
    except Exception as e:
        bad.append(f"{f.name}: {e}")
print(f"{n} compiled models parsed under Snowflake dialect; problems: {bad or 'none'}")
sys.exit(1 if bad else 0)
