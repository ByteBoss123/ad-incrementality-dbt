-- Which age bands drive spend versus conversions inside each campaign.
-- Ratios are ratio of sums; shares are within campaign.
with s as (
    select
        campaign_id,
        age_band,
        sum(spend_usd)            as spend_usd,
        sum(clicks)               as clicks,
        sum(approved_conversions) as approved_conversions
    from {{ ref('agg_campaign_segment_performance') }}
    group by 1, 2
)
select
    campaign_id,
    age_band,
    spend_usd,
    approved_conversions,
    {{ safe_divide('spend_usd', 'approved_conversions') }} as cpa_usd,
    {{ safe_divide('spend_usd', 'clicks') }}               as cpc_usd,
    {{ safe_divide('spend_usd', 'sum(spend_usd) over (partition by campaign_id)') }}                       as spend_share,
    {{ safe_divide('approved_conversions', 'sum(approved_conversions) over (partition by campaign_id)') }} as conversion_share
from s
