"""Compare the Snowflake marts with the independent validation results.

Reads ANALYTICS.DBT_MARTS.* after `dbt build --target snowflake` and checks every
full-release and campaign figure against validation/validation_results.json
(recomputed in pandas, no shared code with the SQL). Writes snowflake/snowflake_run.json.
Exits non-zero on any mismatch. Same auth env vars as load_to_snowflake.py.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[1]
V = json.loads((ROOT / "validation/validation_results.json").read_text())
key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
if key_path:
    from cryptography.hazmat.primitives import serialization
    pk = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=None)
    auth = {"private_key": pk.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                            serialization.NoEncryption())}
else:
    auth = {"password": os.environ["SNOWFLAKE_PASSWORD"]}
con = snowflake.connector.connect(account=os.environ["SNOWFLAKE_ACCOUNT"],
                                  user=os.environ.get("SNOWFLAKE_USER", "DBT_SVC"),
                                  role=os.environ.get("SNOWFLAKE_ROLE", "DBT_ROLE"),
                                  warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                                  database="ANALYTICS", **auth)
q = lambda sql: con.cursor().execute(sql).fetchall()
schema = os.environ.get("SNOWFLAKE_MARTS_SCHEMA", "DBT_MARTS")
fails, got = [], {}


def check(name, sf, ref, tol):
    got[name] = {"snowflake": sf, "validation": ref}
    if abs(float(sf) - float(ref)) > tol:
        fails.append(f"{name}: snowflake={sf} validation={ref}")


for outcome, t_cvr, c_cvr, z, lo in q(f"select outcome, t_cvr, c_cvr, z_stat, abs_lift_ci95_low "
                                      f"from {schema}.FCT_CAMPAIGN_LIFT_FULL"):
    ref = V["experiment_full"][outcome]
    check(f"full.{outcome}.t_rate_pct", 100 * t_cvr, ref["t_rate_pct"], 1e-4)
    check(f"full.{outcome}.c_rate_pct", 100 * c_cvr, ref["c_rate_pct"], 1e-4)
    check(f"full.{outcome}.z", z, ref["z"], 0.01)
    check(f"full.{outcome}.ci_low_pp", 100 * lo, ref["ci95_pp"][0], 1e-4)
(users,), = q(f"select users from {schema}.FCT_ASSIGNMENT_QA_FULL")
check("full.users", users, V["experiment_full"]["users"], 0)
(rate, cace), = q(f"select exposure_rate, cace_conversion from {schema}.FCT_EXPOSURE_EFFECT")
check("full.exposure_rate_pct", 100 * rate, V["experiment_full"]["exposure"]["exposure_rate_pct"], 1e-3)
check("full.cace_conversion_pp", 100 * cace, V["experiment_full"]["exposure"]["cace_conversion_pp"], 1e-3)
for cid, cpa in q(f"select campaign_id, cost_per_approved_conversion_usd from {schema}.AGG_CAMPAIGN_PERFORMANCE"):
    check(f"campaign.{cid}.cpa", cpa, V["campaigns"][str(cid)]["cost_per_approved_conv"], 0.005)

out = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "account": os.environ["SNOWFLAKE_ACCOUNT"],
       "checks": len(got), "mismatches": fails, "values": got}
(ROOT / "snowflake/snowflake_run.json").write_text(json.dumps(out, indent=1, default=float))
print(f"{len(got)} checks, {len(fails)} mismatches")
print("\n".join(fails))
sys.exit(1 if fails else 0)
