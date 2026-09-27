# Sigma layer

## What is implemented in this repo

| Piece | File | Status |
|---|---|---|
| BI-facing dbt views for Sigma (`sigma_lift_summary`, `sigma_campaign_efficiency`, `sigma_replication`) | `models/marts/sigma/` | Built and tested in dbt (PASS on DuckDB) |
| dbt exposure declaring the Sigma workbook as a downstream dashboard | `models/marts/sigma/_sigma.yml` | In the dbt lineage graph |
| Sigma REST API client (token auth, pagination, element lookup, CSV export polling) | `sigma/sigma_client.py` | Unit-tested against a mocked API |
| Automated workbook QA: pulls each Sigma element and checks 20 values against `validation/validation_results.json` | `sigma/verify_workbook.py` | Unit-tested: passes on correct data, catches wrong numbers and missing elements |
| Tests | `sigma/tests/test_sigma.py` | 7/7 pass |

**Status:** built, published and verified on 2026-09-26. See the README for the workbook link and matched values.

## 1. Snowflake (once)

```bash
# Snowsight: run snowflake/setup.sql (uncommented lines)
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
pip install dbt-snowflake snowflake-connector-python pandas pyarrow requests
./fetch_data.sh
python snowflake/load_to_snowflake.py                 # 1,677,052 Criteo rows + 1,143 ads
dbt build --profiles-dir . --target snowflake         # all tests pass
```

The Sigma views land in `ANALYTICS.DBT_SIGMA` and the marts in `ANALYTICS.DBT_MARTS`.

## 2. Connect Sigma

Snowsight: **Admin > Partner Connect > Sigma**. Then run the commented `grant` lines in
`snowflake/setup.sql`.

## 3. Build the workbook

Name it exactly **Ad Incrementality & Campaign Efficiency**. Element titles must match exactly,
because the verifier finds elements by title.

**Page "Incrementality"**

| Element title | Type | Source | Setup |
|---|---|---|---|
| **Lift Summary** | Table | `DBT_SIGMA.SIGMA_LIFT_SUMMARY` | All columns. Format RELATIVE_LIFT and MDE_RELATIVE as %, the *_PP columns as number (3 dp) |
| Visit lift | KPI | Lift Summary | `Max(If([Outcome] = "visit", [Relative Lift]))` |
| Conversion lift | KPI | Lift Summary | `Max(If([Outcome] = "conversion", [Relative Lift]))` |
| **Replication by Sample** | Table | `DBT_SIGMA.SIGMA_REPLICATION` | All columns |
| Replication chart | Bar | Replication by Sample | X = Sample Id, Y = Relative Lift, Color = Outcome |
| **Assignment QA** | Table | `DBT_MARTS.FCT_ASSIGNMENT_QA` | Conditional format Share Gap red when `Abs([Share Gap]) > 0.005` |

**Page "Campaign Efficiency"**

| Element title | Type | Source | Setup |
|---|---|---|---|
| **Campaign Efficiency** | Table | `DBT_SIGMA.SIGMA_CAMPAIGN_EFFICIENCY` | All columns |
| Cost per approved conversion | Bar | Campaign Efficiency | X = Campaign, Y = Cost Per Approved Conversion Usd |
| Spend share | Bar | Campaign Efficiency | X = Campaign, Y = Spend Share |
| Segment CPA | Pivot | `DBT_MARTS.AGG_CAMPAIGN_SEGMENT_PERFORMANCE` | Rows Campaign Id, Age Band; Columns Gender; Value `Sum([Spend Usd]) / Sum([Approved Conversions])` |
| Campaign filter | List control | Campaign | Targets both charts |

Ratios stay sum over sum. Never use `Avg()` on a ratio column.

## 4. Verify the live workbook

In Sigma: **Administration > Developer Access > Create New** (REST API client). Then:

```bash
export SIGMA_CLIENT_ID=... SIGMA_CLIENT_SECRET=... SIGMA_CLOUD=aws   # or gcp / azure
python sigma/verify_workbook.py
# expect: PASS: Sigma workbook 'Ad Incrementality & Campaign Efficiency' matches all 20 independently computed values
```

Screenshot both pages and the PASS line. Those plus the workbook link are the proof.
