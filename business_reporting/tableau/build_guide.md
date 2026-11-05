# Tableau Desktop build guide (draft, not run in Tableau)

Source: `raw/KAG_conversion_data.csv` (1,143 ads). Column names below are the raw names. This guide was written without access to Tableau Desktop in the build environment and has not been executed there.

## 1. Connect
Data > New Data Source > Text file > `raw/KAG_conversion_data.csv`.
In the Data Source tab, change `xyz_campaign_id`, `ad_id` and `fb_campaign_id` to String so they are labels, not measures.

## 2. Calculated fields
Rates use totals, not averages of ad-level ratios. Zero denominators return null.

```
CPA          : IF SUM([Approved_Conversion]) = 0 THEN NULL ELSE SUM([Spent]) / SUM([Approved_Conversion]) END
CTR          : IF SUM([Impressions]) = 0 THEN NULL ELSE SUM([Clicks]) / SUM([Impressions]) END
CPC          : IF SUM([Clicks]) = 0 THEN NULL ELSE SUM([Spent]) / SUM([Clicks]) END
Total Spend  : {FIXED : SUM([Spent])}   (keep out of the table)
Spend Share  : SUM([Spent]) / MIN([Total Spend])
```

Format spend, CPA and CPC as 2-decimal numbers with no currency symbol (currency is unspecified in the source). CTR and Spend Share as percentages.

## 3. Sheets and dashboard
- **Campaign table:** `xyz_campaign_id` on Rows; Measure Names/Values with Spent, Impressions, Clicks, Approved_Conversion, CPA, CTR, CPC, Spend Share; show grand totals.
- **Spend by campaign:** bar chart, `xyz_campaign_id` by SUM(Spent).
- **KPIs:** SUM(Spent), SUM(Approved_Conversion), CPA, CTR.
- Filters on `age` and `gender`, applied to all sheets.
- Dashboard: KPIs on top, table and bar below, filters on the right. Text note: "Currency unspecified. No revenue or ROI data."

## 4. Reconcile before claiming it works
Compare each row with `../validation.json`. Reference values computed from the workbook:

| Campaign | Spend | Approved | CPA |
|---|---|---|---|
| 916 | 149.71 | 24 | 6.24 |
| 936 | 2,893.37 | 183 | 15.81 |
| 1178 | 55,662.15 | 872 | 63.83 |
| Total | 58,705.23 | 1,079 | 54.41 |

Campaign 916 has only 24 approved conversions and 1178 holds about 95% of spend, so the CPA gap is not a scaling or ROI finding. Save a screenshot and record the Tableau version and run date once built.
