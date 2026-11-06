"""Daily build of the ad measurement warehouse (Airflow 3.x).

check_raw -> dbt_build -> validate -> mutation_test
                                   -> export_dashboard

* check_raw:    raw files present, expected columns, SHA-256 matches raw/MANIFEST.sha256
* dbt_build:    all models + 51 data tests; any failing test fails the run
* validate:     independent pandas/statsmodels recomputation; non-empty failures fail the run
* mutation_test: injects 3 known defects into a copy and requires dbt to catch all 3
* export_dashboard: writes the Tableau extracts from the marts
"""
from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT = str(Path(__file__).resolve().parents[1])
CD = f"cd {PROJECT} && "

with DAG(
    dag_id="ad_measurement",
    start_date=datetime(2026, 11, 1),
    schedule="30 5 * * *",
    catchup=False,
    dagrun_timeout=timedelta(hours=1),
    default_args={"owner": "ad-measurement-de", "retries": 1, "retry_delay": timedelta(minutes=5),
                  "execution_timeout": timedelta(minutes=30)},
    tags=["dbt", "measurement"],
) as dag:
    check_raw = BashOperator(task_id="check_raw", bash_command=CD + "python3 orchestration/check_raw.py")
    dbt_build = BashOperator(task_id="dbt_build", bash_command=CD + "dbt build --profiles-dir . --target dev")
    validate = BashOperator(
        task_id="validate",
        bash_command=CD + "python3 validation/validate.py && python3 -c \"import json,sys; "
                          "f=json.load(open('validation/validation_results.json'))['reconciliation_failures']; "
                          "print(f or 'validation OK'); sys.exit(1 if f else 0)\"")
    mutation_test = BashOperator(
        task_id="mutation_test",
        # all 3 injected defects must be caught (dbt reports one ERROR per failing test)
        bash_command=CD + "out=$(bash validation/mutation_test.sh); echo \"$out\"; "
                          "test \"$(echo \"$out\" | grep -oE 'ERROR=[0-9]+' | cut -d= -f2)\" -ge 3",
        retries=0)
    export_dashboard = BashOperator(task_id="export_dashboard", bash_command=CD + "python3 orchestration/export_dashboard.py")

    check_raw >> dbt_build >> validate >> [mutation_test, export_dashboard]
