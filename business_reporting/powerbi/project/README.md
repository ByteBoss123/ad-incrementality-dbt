# Campaign reporting Power BI project

## Open
1. Extract the entire ZIP to one folder.
2. Open `pxpx.pbip` in the same or a newer Power BI Desktop version than the one used to create your original project.
3. Click **Refresh** to load the embedded 1,143-ad snapshot, then save.

Two pages are included: Campaign overview, and Audience and ad detail. Each has campaign, age and gender slicers. The model has Ads and Campaigns with a one-to-many relationship, ten explicit measures, and blank results for zero-denominator ratios.

No source path, sign-in, gateway or cloud subscription is needed for the embedded snapshot. `data/KAG_conversion_data.csv` is an audit copy; editing that CSV does not change the embedded snapshot. The source is the existing ByteBoss123/ad-incrementality-dbt raw export. Dates, revenue and currency code are absent, so no ROAS, profit, time trend or budget-performance claims are made.

## Expected totals before filtering
Ad Count: 1,143. Spend: 58,705.23 source monetary units. Approved Conversions: 1,079. CPA: 54.41. Clicks: 38,165. Impressions: 213,434,828.

## Verification status
Local validation checks JSON against Microsoft's published schemas, model-to-visual field references, layout bounds/overlap, embedded source bytes and independently calculated campaign totals. See `validation/local_checks.json`.

This project has not been opened or rendered in Power BI Desktop here. TMDL parsing, Power Query refresh, DAX execution, native visual appearance and slicer behavior still require the Desktop open/refresh check. Schema validity alone does not prove those runtime behaviors. The plugin's PowerShell review script is not available in this environment.

Open `pxpx.pbip` as the project entry point. Local caches/settings are omitted from the editable project so Desktop rebuilds them. Nothing has been published, and this file does not establish Power BI service administration experience.
