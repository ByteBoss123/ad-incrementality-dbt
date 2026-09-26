# Ad Incrementality & Campaign Performance Analytics Warehouse (dbt)

A dbt project that turns real advertising data into tested, documented measurement
marts. It has two parts: an incrementality readout built on Criteo's randomized
ad-targeting experiments, and a paid-media campaign efficiency layer.

## Data (real-world, public)

| Source | Grain | Rows used | Provenance |
|---|---|---|---|
| Criteo Uplift Modeling Dataset v2.1 (Diemert et al., AdKDD 2018) | user | 821,737 unique users | Real Criteo incrementality tests: users randomly targeted by ads (~85%) or withheld (~15%), with site visit and conversion outcomes. Full release is 13,979,592 rows. Used here: three hash-seeded random samples of the official file, exported with original row positions by the public [UpliftBench](https://github.com/Aman12x/UpliftBench) repo (commit `cc85673`). The official file's hosts are not reachable from the build environment. |
| Facebook ad campaign export (Kaggle "Sales Conversion Optimization") | ad | 1,143 ads | An anonymous organisation's social media ad campaigns, via a [GitHub mirror](https://github.com/mGalarnyk/Python_Tutorials/blob/master/Kaggle/Facebook/KAG_conversion_data.csv). |

Only `row_id`, `y` (outcome) and `w` (treatment) are read from the Criteo files.
The files also contain model-score columns, and staging ignores them.

## Layers

```
sources  (6 Criteo parquet samples, 1 ads CSV)
  └─ staging        stg_criteo__visit_outcomes, stg_criteo__conversion_outcomes,
                    stg_ads__ad_performance                                      (views)
      └─ intermediate   int_criteo__users  (de-duplicated across samples)       (view)
          └─ marts/measurement  fct_campaign_lift, fct_lift_by_sample,
                                fct_experiment_power, fct_assignment_qa,
                                fct_visit_to_conversion                          (tables)
          └─ marts/campaign     fct_ad_performance, agg_campaign_performance,
                                agg_campaign_segment_performance                 (tables)
              └─ marts/sigma    sigma_lift_summary, sigma_campaign_efficiency,
                                sigma_replication  ──> exposure: Sigma workbook  (views)
```

The **Sigma layer** (`sigma/`) has a REST API client and `verify_workbook.py`, which exports
each workbook element from Sigma and checks 20 values against the independent validation
results. Build steps are in `sigma/SIGMA_WORKBOOK.md`.

- 15 models (12 core + 3 Sigma-facing views) and 51 data tests. The tests are built-in, custom generic (`accepted_range`,
  `expression_is_true`) and 4 singular tests: sample de-duplication agreement,
  staging row preservation, lift reconciliation and rollup reconciliation.
- Lift math lives in one macro (`lift_from_counts`), so every readout uses identical formulas.
- Slices with fewer than 10 positives in either arm are marked `is_readable = false`
  and are never flagged significant.
- Every metric is defined in YAML. `dbt docs generate` builds the lineage site.
- Campaign ratios are computed as ratio of sums, never averaged across ads.

## Results (from `validation/validation_results.json`)

**Incrementality.** 698,032 targeted vs 123,705 control users.

| Outcome | Targeted | Control | Absolute lift (95% CI) | Relative | z | Incremental |
|---|---|---|---|---|---|---|
| Visit | 4.845% | 3.828% | +1.017 pp (0.899 to 1.135) | +26.6% | 15.59 | ~7,101 visits |
| Conversion | 0.303% | 0.188% | +0.115 pp (0.087 to 0.142) | +60.8% | 6.96 | ~799 conversions |

**Assignment QA.** Treatment share is 84.93% to 84.97% per sample vs the 85% design.
There is no sample-ratio mismatch (chi-square p = 0.31 to 0.64).

**Power.** At this sample size the minimum detectable effect (80% power) is 0.166 pp for
visits (4.3% relative) and 0.038 pp for conversions (19.9% relative). Both observed
lifts clear it.

**Replication.** Visit lift is stable across the three samples (+23.7% to +30.6%,
Cochran's Q p = 0.33). Conversion lift is not: it ranges from +25.6% to +97.1%
(Q p = 0.043) because each sample has only 64 to 103 control conversions. The pooled
estimate and its CI are the number to report, not any single sample.

**Funnel (descriptive only).** Conversion per visitor is 6.25% targeted vs 4.92% control.
Visiting happens after assignment, so this comparison is not causal.

**Campaigns.** Cost per approved conversion ranges from $6.24 (campaign 916, $150 spend)
to $63.83 (campaign 1178, $55,662 spend, 95% of total). CPC is similar across campaigns
($1.32 to $1.54), so most of the spend goes to the least efficient campaign.

## Verification

| Check | Result |
|---|---|
| `dbt build` | PASS=66 (15 models + 51 tests), 0 warn, 0 error |
| `validation/validate.py`: pandas + statsmodels recomputation from the raw files, no shared code with the SQL | 0 mismatches on rates, z, CIs, campaign CTR / CPA |
| `validation/mutation_test.sh`: inject a conflicting cross-sample duplicate, an invalid treatment code, and clicks > impressions | all 3 caught; downstream marts skipped |
| `pytest sigma/tests`: Sigma client (mocked API) and workbook verifier | 7/7 pass; wrong numbers and missing elements are caught |
| `validation/snowflake_dialect_check.py`: sqlglot parse of all 62 compiled model and schema-test files as Snowflake SQL | 62/62 parse, no DuckDB-only functions |

## Known limits

- **Sample, not the full release.** The 821,737 users are a random ~5.9% of Criteo's
  13.98M rows. The full file could not be downloaded in this environment. Swapping the
  source to the full file only needs a change to `_sources.yml`.
- **No exposure field.** The Criteo `exposure` column and the 12 covariates are not in
  these files, so there is no segment-level or exposure-level analysis.
- **Executed on Snowflake (2026-09-26).** `load_to_snowflake.py` loaded 1,677,052 Criteo rows and
  1,143 ads using key-pair auth, and `dbt build --target snowflake` returned PASS=66 / ERROR=0.
  The Snowflake mart values match the local validation exactly: visit +26.6% (CI 0.899 to 1.135 pp),
  conversion +60.8% (CI 0.087 to 0.142 pp), 698,032 / 123,705 users, and cost per approved
  conversion of $63.83 / $15.81 / $6.24.
- **Sigma: code done, live run pending.** The Sigma views, dbt exposure, API client and verifier
  are implemented and tested offline. The workbook itself, and a `verify_workbook.py` run
  against it, need a Sigma account. The build environment cannot reach Sigma.
- p-values, SRM and replication tests are computed in Python, because a normal CDF is not
  portable across DuckDB and Snowflake SQL.

## Run

```bash
pip install dbt-duckdb statsmodels sqlglot pyarrow
./fetch_data.sh          # Criteo sample files (~57 MB) from the pinned UpliftBench commit
dbt build --profiles-dir .
python validation/validate.py
./validation/mutation_test.sh
dbt compile --profiles-dir . && python validation/snowflake_dialect_check.py
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
```
