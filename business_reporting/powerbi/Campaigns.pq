// Name this query Campaigns. One row per source campaign; no invented names.
let
    Source = Table.SelectColumns(Ads, {"xyz_campaign_id"}),
    UniqueCampaigns = Table.Distinct(Source)
in
    UniqueCampaigns
