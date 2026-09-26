"""Load the raw files into Snowflake RAW.* so dbt can build on Snowflake.

Criteo files: only row_id, y, w are loaded (the model-score columns are not
used by any model). The ads CSV is loaded as-is, all columns as text, with
upper-cased column names so unquoted Snowflake identifiers resolve.

Env: SNOWFLAKE_ACCOUNT plus either
  key pair (default):  SNOWFLAKE_PRIVATE_KEY_PATH, SNOWFLAKE_USER (DBT_SVC), SNOWFLAKE_ROLE (DBT_ROLE)
  password:            SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ROLE (ACCOUNTADMIN)
  optional SNOWFLAKE_WAREHOUSE (COMPUTE_WH).
"""
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

ROOT = Path(__file__).resolve().parents[1]
key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
if key_path:
    from cryptography.hazmat.primitives import serialization
    pkey = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=None)
    auth = {"private_key": pkey.private_bytes(serialization.Encoding.DER,
                                              serialization.PrivateFormat.PKCS8,
                                              serialization.NoEncryption())}
    default_user, default_role = "DBT_SVC", "DBT_ROLE"
else:
    auth = {"password": os.environ["SNOWFLAKE_PASSWORD"]}
    default_user, default_role = None, "ACCOUNTADMIN"
con = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ.get("SNOWFLAKE_USER") or default_user,
    role=os.environ.get("SNOWFLAKE_ROLE", default_role),
    warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    database="RAW",
    **auth,
)

def load(df, schema, table):
    df.columns = [c.upper() for c in df.columns]
    ok, _, nrows, _ = write_pandas(con, df, table, schema=schema, auto_create_table=True,
                                   overwrite=True, quote_identifiers=False)
    print(f"RAW.{schema}.{table}: {nrows:,} rows loaded (success={ok})")
    return nrows

total = 0
for outcome in ["visit", "conversion"]:
    for seed in [42, 43, 44]:
        f = ROOT / f"raw/criteo/predictions_{outcome}_frac0.1_seed{seed}.parquet"
        total += load(pd.read_parquet(f, columns=["row_id", "y", "w"]), "CRITEO", f"{outcome.upper()}_SEED{seed}")
ads = pd.read_csv(ROOT / "raw/KAG_conversion_data.csv", dtype=str)
load(ads, "ADS", "KAG_CONVERSION_DATA")
print(f"Criteo rows loaded: {total:,} (expected 1,677,052)")
