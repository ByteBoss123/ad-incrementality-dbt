# Tableau campaign dashboard

## Open the existing workbook

Download the repository and open `campaign_dashboard.twb` in Tableau Desktop with the adjacent `data` folder intact. The connection uses `data/KAG_conversion_data.csv`. If Tableau prompts for the file, select that included CSV.

The CSV is generated from `../../raw/KAG_conversion_data.csv` with only two header changes: `xyz_campaign_id` becomes `Campaign`, and `Spent` becomes `Spend`. Every row and value is retained. Source currency and campaign dates are unspecified.

## Workbook contents and calculations

The existing Tableau-saved workbook contains Campaign table, Spend by campaign and CPA by campaign worksheets. Its calculations are:

```text
CPA: IF SUM([Approved_Conversion]) = 0 THEN NULL ELSE SUM([Spend]) / SUM([Approved_Conversion]) END
CTR: IF SUM([Impressions]) = 0 THEN NULL ELSE SUM([Clicks]) / SUM([Impressions]) END
CPC: IF SUM([Clicks]) = 0 THEN NULL ELSE SUM([Spend]) / SUM([Clicks]) END
Total Spend: {FIXED : SUM([Spend])}
Spend Share: SUM([Spend]) / MIN([Total Spend])
```

Spend Share uses the full dataset denominator under ordinary age/gender dimension filters. It is not share of selected rows. Adding those filters to context changes the denominator. CPA, CTR and CPC use ratios of sums, not averages of per-ad rates.

## Reconciliation

| Campaign | Spend | Approved | CPA | Share of total spend |
|---|---:|---:|---:|---:|
| 916 | 149.71 | 24 | 6.24 | 0.26% |
| 936 | 2,893.37 | 183 | 15.81 | 4.93% |
| 1178 | 55,662.15 | 872 | 63.83 | 94.82% |
| Total | 58,705.23 | 1,079 | 54.41 | 100.00% |

The existing README records that this workbook was opened, reconciled and re-saved in Tableau Desktop 2026.2 on 2026-11-05. This update preserves that workbook and only changes its data-directory string. The relative-path version was checked structurally and against all source rows, but has not been reopened in Tableau here. Screenshots are still absent.

The CPA differences are descriptive. Campaign 916 has only 24 approved conversions; they do not support a large budget transfer or an ROI claim.
