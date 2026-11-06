# Optional Snowflake execution

The default `dev` target runs locally on DuckDB. Snowflake execution uses your
own account and incurs warehouse usage. Historical results in the root README
are recorded runs, not a guarantee that a cloud environment remains available.

1. Install `dbt-snowflake` and `snowflake-connector-python[pandas]` in the project
   environment, alongside the local dependencies in the root README.
2. Review `setup.sql` with your account administrator. It assumes an existing
   `COMPUTE_WH` warehouse, creates `RAW`/`ANALYTICS` and a `DBT_SVC` service user,
   and grants `DBT_ROLE`. Adapt these names and grants to your environment.
3. Register the service user's public key in Snowflake. Keep the private key
   outside the repository. The current loader expects an unencrypted PEM key;
   protect the file with local permissions. Do not commit keys or passwords.
4. Set `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY_PATH`,
   `SNOWFLAKE_ROLE`, and `SNOWFLAKE_WAREHOUSE` in your local environment.
5. From the repository root, fetch the public input files with `bash fetch_data.sh`.
6. Run `python snowflake/load_to_snowflake.py`. This overwrites the project's
   RAW input tables; use a dedicated project environment. It loads the six sample
   tables, the ads table and, when `raw/criteo_full/criteo_uplift_v2.1.parquet` is present
   (committed), the full release as `RAW.CRITEO.UPLIFT_FULL` (13,979,592 rows).
7. Run `dbt debug --profiles-dir . --target snowflake`, then
   `dbt build --profiles-dir . --target snowflake`.
8. Run `python snowflake/verify_snowflake.py`. It reads the Snowflake marts and compares
   14 figures (full-release rates, z, CI, users, exposure rate, Wald estimate, campaign CPA)
   with `validation/validation_results.json`, writes `snowflake/snowflake_run.json`, and
   exits non-zero on any mismatch.

Steps 6 to 8 in one go (Windows PowerShell, repo root, env vars set):
`powershell -ExecutionPolicy Bypass -File snowflake/run_full_release.ps1`
(writes `snowflake/run_full_release.log`).

Sigma setup is described separately in `sigma/SIGMA_WORKBOOK.md`.
