# One-shot Snowflake run of the full Criteo release (Windows PowerShell, from the repo root).
# Needs the same env vars as before: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH,
# SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE (see snowflake/README.md). Writes snowflake/run_full_release.log.
$ErrorActionPreference = "Stop"
Start-Transcript -Path snowflake/run_full_release.log -Force
foreach ($v in "SNOWFLAKE_ACCOUNT","SNOWFLAKE_PRIVATE_KEY_PATH") {
  if (-not (Test-Path "env:$v")) { throw "Set $v first (see snowflake/README.md)" }
}
python orchestration/check_raw.py;                         if ($LASTEXITCODE) { throw "raw check failed" }
python snowflake/load_to_snowflake.py;                     if ($LASTEXITCODE) { throw "load failed" }
dbt build --profiles-dir . --target snowflake;             if ($LASTEXITCODE) { throw "dbt build failed" }
python snowflake/verify_snowflake.py;                      if ($LASTEXITCODE) { throw "Snowflake marts disagree with validation" }
Stop-Transcript
