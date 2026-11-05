# Campaign business reporting

This extension brings the existing 1,143-ad campaign dataset into an Excel reporting workbook and provides Microsoft Power BI and Access implementation drafts. It does not change the original dbt models or claim a live Microsoft deployment.

## Open the completed workbook

Download [campaign_reporting.xlsx](excel/campaign_reporting.xlsx). The Campaigns sheet contains formula-driven campaign comparisons, a CPA chart and an editable ad-ID lookup. The Ads sheet preserves all source records. SUMIFS aggregates spend and counts; XLOOKUP retrieves ad details. Ratios use sums, with zero denominators shown as unavailable.

The workbook is a static source snapshot with editable data, not a connected live report. Its 3 campaign rows reflect the existing dataset. When adding a new campaign, add a summary row, extend the total and chart, and rerun reconciliation. Adding ad rows to the Excel Table extends structured formula references. Source currency and campaign dates are unspecified.

## Finish the native Excel exercise

1. Open a copy of the workbook in Excel for Windows and save it as `.xlsm`.
2. Open the VBA editor, import [ReportingMacros.bas](excel/ReportingMacros.bas), and review the code.
3. Run `BuildCampaignPivot`. It creates a native PivotTable with campaign and age rows, a gender filter, and summed spend, conversions, clicks and impressions.
4. Run `RefreshReport` after editing data. Verify the PivotTable grand totals against `validation.json`. Do not average ad-level CPA values.
5. Save a screenshot showing the PivotTable and filter, and record Excel version and run date.

The delivered `.xlsx` contains no embedded macros or native PivotTable. The VBA source is provided separately and has not been run in Excel. A native-app run is required before claiming that exercise as completed.

## Power BI Desktop draft

1. Create a text parameter `SourcePath` pointing at `raw/KAG_conversion_data.csv`.
2. Create blank queries `Ads` and `Campaigns`, paste their `.pq` files into Advanced Editor, and enable load.
3. Add a one-to-many relationship `Campaigns[xyz_campaign_id]` -> `Ads[xyz_campaign_id]`, single-direction filtering from Campaigns to Ads. Confirm Campaigns keys are unique.
4. Create the measures from `powerbi/measures.dax` individually. Format CTR and approval/spend shares as percentages. Format spend, CPC and CPA as decimals, without assuming a currency.
5. Build page **Campaign overview**: spend and approved-conversion cards, campaign CPA bar chart, campaign table, and campaign/age/gender slicers.
6. Build page **Ad detail**: ad ID, campaign, age, impressions, clicks, spend, total and approved conversions. Enable campaign drill-through and add a back button. Verify that totals reconcile under filters.
7. Save the project as PBIP. Compare all 3 campaigns with `validation.json`, test slicers and drill-through, and capture screenshots.

The `.pq` and `.dax` files are implementation drafts, not a PBIX/PBIP or proof of dashboard execution. Power BI Desktop is unavailable in the build environment. A Windows PowerShell model-wizard runtime is also unavailable, so the model design and source drafts are supplied explicitly.

For multiple-source practice, connect to the existing Snowflake campaign and lift views in this repository once authorized and credentials are available. Keep the unrelated Criteo experiment population separate from the Facebook ad population. Do not join them as if they describe the same campaign.

## Tableau Desktop dashboard

Follow [tableau/build_guide.md](tableau/build_guide.md), or open [tableau/campaign_dashboard.twb](tableau/campaign_dashboard.twb) in Tableau Desktop. The workbook has a campaign table, spend and CPA bar charts, and CPA, CTR, CPC and spend-share calculated fields. It reads a local copy of `raw/KAG_conversion_data.csv` with `Campaign` and `Spend` columns, so relink the data file when Tableau asks. It was written by hand as TWB XML, not exported from Tableau.

Checked on 2026-11-05 in Tableau Desktop 2026.2 (Free Edition): the workbook opened, and approved conversions, CPA, CPC, CTR, clicks, impressions and spend for campaigns 916, 936 and 1178 matched `validation.json`. Age and gender filters rendered. **Known issue:** the Spend Share column showed 100% for every campaign, both with `TOTAL()` and, in a later revision, with an `EXCLUDE` LOD, and the committed workbook has not been seen showing correct shares. Treat Spend Share as not working. The other columns are the verified ones. There is no saved screenshot, and no Tableau proficiency is inferred from generated XML.

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

Tests cover source totals, duplicate IDs, invalid counts/spend and zero denominators. Python and SQLite independently agree on campaign totals. The Excel authoring run reconciled every campaign's spend, approved conversions and CPA, tested source-edit recalculation, and tested an unknown ad lookup. The workbook was rendered and reviewed. Native Excel, VBA, Power Query, DAX and Access execution remain pending.

`excel/build.mjs` records the workbook builder. It requires the `@oai/artifact-tool` runtime; the prebuilt workbook can be opened without that package. Run `node build.mjs <repository-root> <absolute-output-directory>` from an environment where that package resolves.

## Portfolio evidence versus skills

| Requirement | Existing repository evidence / addition | Remaining evidence |
|---|---|---|
| Marketing analytics | Ad incrementality, email campaign lift, GA4 conversion diagnostics | Explain assumptions and findings independently |
| SQL and source transformation | Existing dbt models and validation; reporting reconciliation | Demonstrate an end-to-end rerun |
| Advanced Excel | Formula workbook, ad lookup, native chart | Run VBA/PivotTable, test filters and refresh in Excel |
| Power BI | M queries, model design, DAX measures and page specification | Build/save PBIP and validate in Desktop |
| Power BI administration | Operational exercise in `powerbi/service_exercise.md` | Live workspace/refresh/access evidence |
| Access | Schema, saved-query SQL, database builder | Run in Access, inspect relationships and query results |
| SAP/FICO | No evidence found in this review | Optional learning; not claimed |

Generated materials support practice. They do not establish prior employment experience or independent proficiency. Only add completed, explainable work to a resume.

## API references

- [Microsoft PivotCaches.Create](https://learn.microsoft.com/en-us/office/vba/api/excel.pivotcaches.create)
- [Microsoft Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document)
- [Microsoft Access NewCurrentDatabase](https://learn.microsoft.com/en-us/office/vba/api/access.application.newcurrentdatabase)
