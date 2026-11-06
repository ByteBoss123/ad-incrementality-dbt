# Campaign business reporting

This extension provides Tableau, Power BI and Excel reporting for the existing 1,143-ad campaign dataset. Access and VBA exercises remain separate drafts. Existing dbt models are unchanged; Power BI service deployment is not claimed.

## Open the completed workbook

Download [campaign_reporting.xlsx](excel/campaign_reporting.xlsx). The Campaigns sheet contains formula-driven campaign comparisons, a CPA chart and an editable ad-ID lookup. The Ads sheet preserves all source records. SUMIFS aggregates spend and counts; XLOOKUP retrieves ad details. Ratios use sums, with zero denominators shown as unavailable.

The workbook is a static source snapshot with editable data, not a connected live report. Its 3 campaign rows reflect the existing dataset. When adding a new campaign, add a summary row, extend the total and chart, and rerun reconciliation. Adding ad rows to the Excel Table extends structured formula references. Source currency and campaign dates are unspecified.

## Finish the native Excel exercise

1. Open a copy of the workbook in Excel for Windows and save it as `.xlsm`.
2. Open the VBA editor, import [ReportingMacros.bas](excel/ReportingMacros.bas), and review the code.
3. Run `BuildCampaignPivot`. It creates a native PivotTable with campaign and age rows, a gender filter, and summed spend, conversions, clicks and impressions.
4. Run `RefreshReport` after editing data. Verify the PivotTable grand totals against `validation.json`. Do not average ad-level CPA values.
5. Save a screenshot showing the PivotTable and filter, and record Excel version and run date.

`excel/campaign_reporting.xlsx` contains no embedded macros or native PivotTable. `excel/campaign_reporting_pivot.xlsx` is a copy with a native PivotTable on `Sheet1`, built by hand in desktop Excel on 2026-11-05 through the PivotTable Fields pane (campaign and age in Rows, gender as a filter, summed impressions, clicks, spend and approved conversions), not by the macro. Its grand totals match `validation.json`: spend 58,705.23, approved 1,079, clicks 38,165, impressions 213,434,828, and the per-campaign rows match too. The VBA in `ReportingMacros.bas` has still not been run in Excel, so the macro exercise is not claimed as completed. The Access draft has not been run, because Access is not installed on the test machine. There is no saved screenshot and the Excel version was not recorded.

## Power BI project

Open [powerbi/project/pxpx.pbip](powerbi/project/pxpx.pbip) after downloading the complete repository, then select **Refresh** in Power BI Desktop. The dataset is embedded; no local source path or sign-in is required. Keep the `.Report` and `.SemanticModel` folders beside the PBIP.

- **Campaign overview:** spend, approved-conversion, CPA and CTR cards; campaign spend and CPA charts; campaign metrics table.
- **Audience and ad detail:** age-band charts and ad-level detail.
- Both pages have campaign, age and gender slicers. The model has Ads and Campaigns, a one-to-many relationship and ten explicit measures.

Local validation covered 21 report JSON files against Microsoft schemas, 16 visual definitions, field references, layout bounds and embedded source reconciliation. This is not Desktop execution: TMDL parsing, Power Query refresh, DAX evaluation and rendered slicer behavior still require a native-app check. See [project validation](powerbi/project/validation/local_checks.json).

The standalone `.pq`/`.dax` files in `powerbi/` describe the earlier manual-build route and use its original field names. The PBIP contains its own authoritative TMDL queries and measures. Do not paste the older drafts into the new project. No drill-through action or service deployment is claimed.

For multiple-source practice, connect to the existing Snowflake views only when credentials are available. Keep the unrelated Criteo experiment and Facebook ad populations separate.

## Tableau Desktop dashboard

Follow [tableau/build_guide.md](tableau/build_guide.md), or open [tableau/campaign_dashboard.twb](tableau/campaign_dashboard.twb) in Tableau Desktop. The workbook has a campaign table, spend and CPA bar charts, and CPA, CTR, CPC and spend-share calculated fields. It reads the included `tableau/data/KAG_conversion_data.csv`: `xyz_campaign_id` is renamed `Campaign` and `Spent` is renamed `Spend`; all 1,143 rows and values are preserved. The connection now uses the relative `data` directory. If Tableau asks to locate the source, select that CSV. It was first written by hand as TWB XML, then opened and re-saved in Tableau.

The existing repository notes record the following check on 2026-11-05 in Tableau Desktop 2026.2 (Free Edition): the workbook opened, and approved conversions, CPA, CPC, CTR, clicks, impressions, spend and spend share for campaigns 916, 936 and 1178 matched `validation.json` (spend share 0.26%, 4.93%, 94.82%). Age and gender filters rendered. Spend share uses a separate `{FIXED : SUM([Spend])}` total field, so its denominator ignores the age and gender filters. Earlier `TOTAL()` and single-formula `EXCLUDE`/`FIXED` versions showed 100% for every campaign. The Grand Total row was turned on in Tableau and read approved 1,079, CPA 54.41, CPC 1.54, CTR 0.018%, clicks 38,165, impressions 213,434,828, spend 58,705 and spend share 100%, and the workbook in this folder is that Tableau-saved file. There is no saved screenshot. This update checked the portable connection and data locally; it did not rerun Tableau Desktop.

## Microsoft Access draft

From Windows PowerShell with Microsoft Access installed:

```powershell
.\business_reporting\access\Build-Access.ps1
```

The script creates a new `.accdb`, two tables with primary/foreign keys, parameterized inserts, and a saved `CampaignTotals` query. It refuses to overwrite an existing database. Open the saved query and reconcile each campaign to `validation.json`. A failed run may leave a partial database: inspect it and choose a new output filename for a retry.

Access and PowerShell are unavailable here. The script and Access SQL have not been executed in their target engines. No `.accdb` is included and no Access proficiency is inferred from generated code.

## Reproduce the verified calculations

From the repository root:

```bash
python business_reporting/validate.py
python -m unittest discover -s business_reporting -p 'test_*.py'
```

Tests cover source totals, duplicate IDs, invalid counts/spend and zero denominators. Python and SQLite independently agree on campaign totals. The Excel authoring run reconciled every campaign's spend, approved conversions and CPA, tested source-edit recalculation, and tested an unknown ad lookup. The workbook was rendered and reviewed. The repository separately records a native Excel PivotTable check. VBA, Power BI runtime and Access execution remain pending.

`excel/build.mjs` records the workbook builder. It requires the `@oai/artifact-tool` runtime; the prebuilt workbook can be opened without that package. Run `node build.mjs <repository-root> <absolute-output-directory>` from an environment where that package resolves.

## Portfolio evidence versus skills

| Requirement | Existing repository evidence / addition | Remaining evidence |
|---|---|---|
| Marketing analytics | Ad incrementality, email campaign lift, GA4 conversion diagnostics | Explain assumptions and findings independently |
| SQL and source transformation | Existing dbt models and validation; reporting reconciliation | Demonstrate an end-to-end rerun |
| Advanced Excel | Formula workbook, ad lookup, chart and recorded native PivotTable check | Execute VBA and record refresh evidence |
| Power BI | Editable two-page PBIP with model and measures; local checks passed | Open/refresh and verify visuals in Desktop |
| Tableau | Tableau-saved workbook; prior Desktop check documented | Recheck portable source path and capture screenshots |
| Power BI administration | Operational exercise in `powerbi/service_exercise.md` | Live workspace/refresh/access evidence |
| Access | Schema, saved-query SQL, database builder | Run in Access, inspect relationships and query results |
| SAP/FICO | No evidence found in this review | Optional learning; not claimed |

Generated materials support practice. They do not establish prior employment experience or independent proficiency. Only add completed, explainable work to a resume.

## API references

- [Microsoft PivotCaches.Create](https://learn.microsoft.com/en-us/office/vba/api/excel.pivotcaches.create)
- [Microsoft Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document)
- [Microsoft Access NewCurrentDatabase](https://learn.microsoft.com/en-us/office/vba/api/access.application.newcurrentdatabase)
