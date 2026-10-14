# Snowflake execution and evidence

The repository README records a September 26, 2026 Snowflake execution and Sigma publication.
The October 14 review reran the local DuckDB build and independent validation; it did not connect to Snowflake or Sigma.
Local SQL parsing is not proof of cloud execution.

## Reproduce locally

Follow the root README. `dbt build --profiles-dir .` runs 17 models and 57 tests.
`python validation/validate.py` independently checks results against raw data.
`python validation/snowflake_dialect_check.py` parses compiled SQL using the Snowflake dialect.

## Reproduce on your authorized Snowflake account

Use `setup.sql`, the `snowflake` profile in `profiles.yml`, and `load_to_snowflake.py`.
Configure account, user, warehouse, role, and the private-key file path through the documented environment variables.
Keep keys and credentials outside Git. Install the Snowflake connector and dbt-snowflake in your environment.
Run `dbt build --profiles-dir . --target snowflake` after loading the source data.

Preserve sanitized dbt run results, the commit SHA, execution date, and the independently reconciled mart outputs
to support a cloud-execution claim. The current review does not manufacture missing historical execution logs.

## Decision supported

Determine whether randomized ad targeting changed visits/conversions, and investigate descriptive campaign-cost differences.
The randomized lift estimates do not establish that reallocating spend between the separate Facebook campaigns will cause savings.
The same tested SQL/reporting practices transfer to operations analytics, but this dataset is marketing data.
