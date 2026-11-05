// Create a text parameter SourcePath pointing to raw/KAG_conversion_data.csv.
// Name this query Ads. Draft: validate in Power BI Desktop or Excel Power Query.
let
    Source = Csv.Document(File.Contents(SourcePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"ad_id", type text}, {"xyz_campaign_id", type text}, {"fb_campaign_id", type text},
        {"age", type text}, {"gender", type text}, {"interest", Int64.Type},
        {"Impressions", Int64.Type}, {"Clicks", Int64.Type}, {"Spent", type number},
        {"Total_Conversion", Int64.Type}, {"Approved_Conversion", Int64.Type}}, "en-US"),
    Invalid = Table.SelectRows(Typed, each [ad_id] = null or [xyz_campaign_id] = null or
        [Impressions] = null or [Clicks] = null or [Spent] = null or
        [Total_Conversion] = null or [Approved_Conversion] = null or
        [Impressions] < 0 or [Clicks] < 0 or [Spent] < 0 or
        [Total_Conversion] < 0 or [Approved_Conversion] < 0 or
        [Clicks] > [Impressions] or [Approved_Conversion] > [Total_Conversion]),
    Checked = if Table.RowCount(Invalid) > 0 then error "Invalid ad records. Inspect source; do not silently remove rows."
        else if Table.RowCount(Table.Distinct(Typed, {"ad_id"})) <> Table.RowCount(Typed)
        then error "Duplicate ad IDs" else Typed
in
    Checked
