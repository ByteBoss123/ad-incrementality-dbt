# Ad Incrementality & Campaign Performance Analytics Warehouse

**Stack:** dbt, Snowflake, SQL, Python, Airflow; reporting in Tableau, Power BI, Excel and Sigma (DuckDB for local runs)

**Campaign reporting:** [Tableau workbook](business_reporting/tableau/campaign_dashboard.twb), [Power BI project](business_reporting/powerbi/project/pxpx.pbip), and [Excel PivotTable workbook](business_reporting/excel/campaign_reporting_pivot.xlsx). Download the repository to keep each project and its data together. [Setup and validation status](business_reporting/README.md).

| Reporting tool | Artifact | Verification status |
|---|---|---|
| Tableau | Campaign table, spend and CPA charts, age/gender filters | Existing repository notes record a Desktop 2026.2 check; portable source path and CSV checked locally |
| Power BI | Two pages, 16 visuals including slicers, two-table model, 10 DAX measures | Report JSON/schema and source checks passed; Desktop refresh/render still pending |
| Excel | Formula report and native PivotTable | Existing repository notes record desktop reconciliation; VBA execution pending |
| Tableau (measurement) | `tableau/Ad_Measurement.twb`: lift, exposure, assignment QA, campaign CPA | Opened and saved in Tableau Desktop 2026.2 |
| Sigma | Snowflake-connected workbook (retired; account suspended) | Prior publication and verification documented below |


## Business Problem
An advertiser spending on paid media needs two answers: **did the ads actually cause extra visits and
conversions, or would those customers have converted anyway?** And **where is the budget being wasted?**
Attribution dashboards cannot answer the first question; only a randomized holdout can. The answer is
only trustworthy if the data, the statistics and the reporting layer are all tested.

## Steps Taken to Resolve
1. **Sourced real experiment data:** the full Criteo randomized ad-targeting release, 13,979,592 users (~85% could see ads, ~15% held out), plus three 2% samples for sensitivity checks and 1,143 Facebook ads across 3 campaigns ($58.7K spend).
2. **Modeled a tested dbt layer:** 22 models with 70 data tests across staging, intermediate, marts and Sigma-facing views; all lift math lives in one macro so every readout uses identical formulas.
3. **Built experiment QA into the models:** sample-ratio checks, minimum detectable effect at 80% power, a readability guardrail for small slices, an exposure (complier) analysis, and a test that every sampled row matches the full release.
4. **Decomposed campaign efficiency:** split each campaign's cost-per-conversion gap into click cost (CPC) versus click-to-conversion rate, and profiled spend and conversions by age band.
5. **Deployed to Snowflake and Sigma, then Tableau:** loaded the samples with key-pair auth, ran `dbt build` on Snowflake, and published a Sigma workbook (since retired); then ran the full release on Snowflake (`snowflake/run_full_release.ps1`); orchestrated in Airflow with a Tableau dashboard.
6. **Verified every number independently:** recomputed all results in pandas/statsmodels with no shared code, and ran mutation tests that inject bad data to prove the tests catch it.

## Achievements
- Measured **+27.1% visits and +59.4% conversions** caused by the ads on the full 13.98M-user release (z = 65.25 / 28.52), with no sample-ratio mismatch (p = 0.999).
- Only **3.6%** of targeted users were exposed; the effect per exposed user is **+3.20 pp** on conversion, and the naive exposed-vs-control comparison overstates it by about 60%.
- Found a **10x cost-per-conversion gap**: **93%** of it comes from click-to-conversion rate, not click cost; ages 45-49 take **34%** of the top campaign's spend at **3x** the CPA of ages 30-34.
- **Caught and fixed a Snowflake precision bug** (fixed-point division) that inflated visit z-scores by about 3%, and added an automated check that blocks it from coming back.
- Ran the full 13.98M-user release on **Snowflake** (`dbt build` PASS=92); all 14 checked Snowflake values match an independent pandas recompute.
- **Caught a second Snowflake precision bug** (`AVG` on integers keeps 6 decimals) through that cross-check, and added a static check that blocks it.

## Data (real-world, public)

| Source | Grain | Rows used | Provenance |
|---|---|---|---|
| Criteo Uplift Modeling Dataset v2.1, **full release** (Diemert et al., AdKDD 2018) | user | 13,979,592 users | Real Criteo incrementality tests: users randomly targeted by ads (85%) or withheld (15%), with visit, conversion and exposure flags. Official `criteo-research-uplift-v2.1.csv.gz` from Hugging Face `criteo/criteo-uplift` (SHA-256 `2716e1bf0fd157a93b5bf86924d9088419dfbac2022c6cd90030220634f616dc`), column-projected to the four flags (`raw/criteo_full/`). |
| Criteo v2.1 samples (replication) | user | 821,737 unique users | Three hash-seeded 2% samples of the official file with original row positions, from the public [UpliftBench](https://github.com/Aman12x/UpliftBench) repo (commit `cc85673`). Every sampled row matches the full release at its row position (singular test `assert_samples_match_full_release`). |
| Facebook ad campaign export (Kaggle "Sales Conversion Optimization") | ad | 1,143 ads | An anonymous organisation's social media ad campaigns, via a [GitHub mirror](https://github.com/mGalarnyk/Python_Tutorials/blob/master/Kaggle/Facebook/KAG_conversion_data.csv). |

From the full release only `treatment`, `conversion`, `visit` and `exposure` are kept
(`orchestration/compact_criteo.py`). From the sample files only `row_id`, `y` (outcome) and
`w` (treatment) are read; their model-score columns are ignored.

## Layers

```
sources  (Criteo full release, 6 Criteo samples, 1 ads CSV)
  └─ staging        stg_criteo__full_release, stg_criteo__visit_outcomes,
                    stg_criteo__conversion_outcomes, stg_ads__ad_performance     (views)
      └─ marts/measurement_full  fct_campaign_lift_full, fct_experiment_power_full,
                                 fct_assignment_qa_full, fct_exposure_effect     (tables)
      └─ intermediate   int_criteo__users  (de-duplicated across samples)       (view)
          └─ marts/measurement  fct_campaign_lift, fct_lift_by_sample,
                                fct_experiment_power, fct_assignment_qa,
                                fct_visit_to_conversion                          (tables)
          └─ marts/campaign     fct_ad_performance, agg_campaign_performance,
                                agg_campaign_segment_performance,
                                fct_cpa_drivers, fct_segment_cpa_drivers         (tables)
              └─ marts/sigma    sigma_lift_summary, sigma_campaign_efficiency,
                                sigma_replication  ──> exposure: Sigma workbook  (views)
```

The **Sigma layer** (`sigma/`, retired, see Known limits) has a REST API client and `verify_workbook.py`, which exports
each workbook element from Sigma and checks 20 values against the independent validation
results. Build steps are in `sigma/SIGMA_WORKBOOK.md`.

- 22 models (19 core + 3 Sigma-facing views) and 70 data tests. The tests are built-in, custom generic (`accepted_range`,
  `expression_is_true`) and 4 singular tests: sample de-duplication agreement,
  staging row preservation, lift reconciliation and rollup reconciliation.
- Lift math lives in one macro (`lift_from_counts`), so every readout uses identical formulas.
- Slices with fewer than 10 positives in either arm are marked `is_readable = false`
  and are never flagged significant.
- Every metric is defined in YAML. `dbt docs generate` builds the lineage site.
- Campaign ratios are computed as ratio of sums, never averaged across ads.

## Results (from `validation/validation_results.json`)

**Incrementality, full release.** 11,882,655 targeted vs 2,096,937 control users.

| Outcome | Targeted | Control | Absolute lift (95% CI) | Relative | z | Incremental |
|---|---|---|---|---|---|---|
| Visit | 4.854% | 3.820% | +1.034 pp (1.006 to 1.063) | +27.1% | 65.25 | ~122,895 visits |
| Conversion | 0.309% | 0.194% | +0.115 pp (0.108 to 0.122) | +59.4% | 28.52 | ~13,687 conversions |

The 2% samples gave +26.6% and +60.8%; the full release narrows the conversion CI about 5x.

**Exposure.** Only 3.604% of targeted users were actually exposed to an ad, and no control user
was. The effect per exposed user (Wald / complier-average estimate, ITT divided by the exposure
rate) is +3.20 pp on conversion. Comparing exposed users with control directly gives +5.18 pp,
which overstates the causal effect by about 60% because exposure depends on user activity.
The Wald estimate assumes targeting has no effect on users who were never exposed.

**Assignment QA.** Full release treatment share 85.00001% vs the 85% design, chi-square p = 0.999.
Per sample: 84.93% to 84.97%, p = 0.31 to 0.64.

**Cross-sample sensitivity (samples, not independent replication).** Visit lift is stable across the three samples (+23.7% to +30.6%,
Cochran's Q p = 0.33). Conversion lift is not: it ranges from +25.6% to +97.1%
(Q p = 0.043) because each sample has only 64 to 103 control conversions. The samples overlap (16,701 users occur in multiple samples), so the reported
Cochran Q p-values are exploratory and do not establish independent replication.
Use the pooled, deduplicated estimate and its CI rather than a single sample. The full release resolves conversion lift at +59.4%.

**Power.** At full scale the minimum detectable effect (80% power) is 0.040 pp for visits (1.1%
relative) and 0.0092 pp for conversions (4.8% relative), down from 19.9% relative on the samples.

**Funnel (descriptive only).** Conversion per visitor is 6.25% targeted vs 4.92% control (samples).
Visiting happens after assignment, so this comparison is not causal.

**Campaigns.** Cost per approved conversion ranges from $6.24 (campaign 916, $150 spend)
to $63.83 (campaign 1178, $55,662 spend, 95% of total). CPC is similar across campaigns
($1.32 to $1.54), so most of the spend goes to the least efficient campaign.

**CPA drivers (`fct_cpa_drivers`, `fct_segment_cpa_drivers`).** CPA = CPC x clicks per approved
conversion, so the log gap to the best campaign splits exactly into a click-cost part and a
click-to-conversion part. For campaign 1178 (10.2x the CPA of campaign 916), 93.4% of the gap comes from
click-to-conversion rate (41.4 vs 4.7 clicks per approved conversion) and 6.6% from CPC. Inside 1178,
CPA rises with every age band: ages 45-49 take 34.2% of spend but 19.4% of approved conversions
($112.71 CPA), versus 26.6% of spend and 45.3% of conversions for ages 30-34 ($37.43 CPA). Both are
recomputed independently in `validate.py`.

## Orchestration

`dags/ad_measurement.py` (Airflow 3.x, daily): `check_raw` (files present, expected columns,
SHA-256 vs `raw/MANIFEST.sha256`) -> `dbt_build` -> `validate` (fails on any reconciliation
mismatch) -> `mutation_test` (all 3 injected defects must be caught) and `export_dashboard`.
Verified with `airflow dags test` on Airflow 3.1.8: all 5 tasks succeeded.

## Dashboard

`tableau/Ad_Measurement.twb` (Tableau 2026.2) reads the CSV extracts written by
`orchestration/export_dashboard.py`: targeted vs control rates, lift readout, replication by
sample, effect per exposed user, assignment QA, campaign cost per approved conversion, and the
largest campaign by segment. It replaces the earlier Sigma workbook (the Sigma account is suspended).

## Verification

| Check | Result |
|---|---|
| `dbt build` (DuckDB) | PASS=92 (22 models + 70 tests), 0 warn, 0 error |
| `assert_samples_match_full_release` | all 821,737 sampled users match the full release at their row position |
| `validation/validate.py`: pandas + statsmodels recomputation from the raw files, no shared code with the SQL | 0 mismatches on rates, z, CIs, exposure rate, Wald estimate, campaign CTR / CPA, CPA drivers |
| `validation/mutation_test.sh`: inject a conflicting cross-sample duplicate, an invalid treatment code, and clicks > impressions | all 3 caught (4 failing tests: the full-release provenance test also flags the corrupted row); downstream marts skipped |
| `airflow dags test ad_measurement` | 5/5 tasks succeeded |
| `pytest sigma/tests business_reporting/test_reporting.py` | 11/11 pass |
| `validation/snowflake_dialect_check.py`: sqlglot parse of all 87 compiled model and schema-test files as Snowflake SQL | 87/87 parse, no DuckDB-only functions, no reserved-word aliases, no fixed-point divisions or uncast `AVG` |
| Full release on Snowflake (2026-11-06): `load_to_snowflake.py` + `dbt build --target snowflake` | 13,979,592 rows loaded to `RAW.CRITEO.UPLIFT_FULL`; PASS=92, 0 warn, 0 error |
| `snowflake/verify_snowflake.py`: Snowflake marts vs `validation_results.json` | 14/14 match (rates, z, CI, users, exposure rate, Wald estimate, campaign CPA); `snowflake/snowflake_run.json` |

## Known limits

- **Four columns of the full release.** The 12 anonymized covariates (f0-f11) are not loaded, so
  there is no covariate adjustment (CUPED) or segment-level uplift on the full release.
- **Full release on Snowflake (2026-11-06).** `load_to_snowflake.py` loaded all 13,979,592 rows to
  `RAW.CRITEO.UPLIFT_FULL` with key-pair auth, and `dbt build --target snowflake` returned PASS=92 / ERROR=0.
  `verify_snowflake.py` then compared 14 Snowflake mart values with the independent pandas results:
  visit +27.1% (z = 65.25), conversion +59.4% (z = 28.52), exposure rate 3.604%, effect per exposed user
  +3.196 pp, cost per approved conversion $6.24 / $15.81 / $63.83. All 14 match (`snowflake/snowflake_run.json`).
- **Second Snowflake precision bug, found by that check.** The first full-release run passed `dbt build`
  but failed 1 of 14 checks: the effect per exposed user was 3.1940 pp on Snowflake vs 3.1964 pp in pandas.
  `AVG` over an integer column returns NUMBER with 6 decimals on Snowflake, which truncated the arm conversion
  rates (~0.003) before the difference was taken. `fct_exposure_effect` now averages doubles, the rerun matched
  exactly, and `snowflake_dialect_check.py` fails on any uncast `AVG`.
- **Executed on Snowflake (2026-09-26).** `load_to_snowflake.py` loaded 1,677,052 Criteo rows and
  1,143 ads using key-pair auth, and `dbt build --target snowflake` returned PASS=66 / ERROR=0.
  The Snowflake mart values match the local validation exactly: visit +26.6% (CI 0.899 to 1.135 pp),
  conversion +60.8% (CI 0.087 to 0.142 pp), 698,032 / 123,705 users, and cost per approved
  conversion of $63.83 / $15.81 / $6.24.
- **Snowflake precision bug, found and fixed.** Querying the Sigma view on Snowflake showed
  z = 16.03 and MDE = 0.161 pp for visits, against 15.59 and 0.166 pp from the validation.
  Snowflake's fixed-point division keeps about 6 decimals, so `1.0 / 698032` became 0.000001
  and the pooled standard errors came out about 5% too small. DuckDB uses floating point, so
  local runs never showed it. Every division now casts to `double`, and
  `snowflake_dialect_check.py` fails on any division that doesn't.
  After the fix, `dbt build --target snowflake` again returned PASS=66, and the Snowflake view gives
  z = 15.59 / 6.96 and MDE = 0.1658 / 0.0375 pp, matching the validation.
- **Sigma: published and verified (2026-09-26).** Workbook "Ad Incrementality & Campaign Efficiency"
  (https://app.sigmacomputing.com/george-mason-university/workbook/Ad-Incrementality-and-Campaign-Efficiency-1KGcOqLiT16T3wx87f0ZH2)
  has 4 Custom SQL elements on the Snowflake connection: lift summary, replication by sample, assignment QA
  and campaign efficiency. Querying the published elements through Sigma returned z = 15.59 / 6.96,
  lift +26.6% / +60.8%, per-sample lift 30.6 / 25.7 / 23.7% (visit), treatment share 84.93-84.97%, and
  cost per approved conversion $63.83 / $15.81 / $6.24, all matching `validation_results.json`.
- **Sigma retired.** The Sigma account is suspended. The Sigma views, exposure and API client remain in
  `sigma/` and `models/marts/sigma/` as a record; the dashboard of record is now Tableau.
- p-values, SRM and replication tests are computed in Python, because a normal CDF is not
  portable across DuckDB and Snowflake SQL.

## Run

```bash
python -m pip install dbt-duckdb statsmodels sqlglot pyarrow pandas pytest requests
bash fetch_data.sh          # Criteo sample files (~57 MB) from the pinned UpliftBench commit
# raw/criteo_full/ is committed (19.6 MB, 4 columns). To rebuild it from the official file:
#   download criteo-research-uplift-v2.1.csv.gz from huggingface.co/datasets/criteo/criteo-uplift
#   python orchestration/compact_criteo.py <path/to/criteo-research-uplift-v2.1.csv.gz>
python orchestration/check_raw.py
dbt build --profiles-dir .
python validation/validate.py
bash validation/mutation_test.sh
dbt compile --profiles-dir . && python validation/snowflake_dialect_check.py
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
```


## Reproducing optional integrations

See [Snowflake setup](snowflake/README.md) for the cloud loader and dbt target.
The local DuckDB workflow needs no Snowflake credentials. To test the mocked
Sigma integration without contacting Sigma, run `python -m pytest sigma/tests -q`.
The verification table records prior executions, not continuous service health.
