-- BI-facing campaign table for Sigma. spend_share is computed here (ratio of
-- sums) so the dashboard cannot accidentally average per-row ratios.
with c as (select * from {{ ref('agg_campaign_performance') }})

select
    cast(campaign_id as varchar)                                  as campaign,
    ads,
    impressions,
    clicks,
    spend_usd,
    approved_conversions,
    ctr,
    cpc_usd,
    cost_per_approved_conversion_usd,
    {{ safe_divide('spend_usd', 'sum(spend_usd) over ()') }}      as spend_share
from c
