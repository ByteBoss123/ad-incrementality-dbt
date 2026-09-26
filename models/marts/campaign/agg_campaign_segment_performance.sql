-- Ratios are recomputed from summed numerators and denominators (ratio of
-- sums), never averaged across ads, so small ads cannot distort the rollup.
with ads as (
    select * from {{ ref('fct_ad_performance') }}
),

rolled as (
    select
        campaign_id,age_band,gender,
        count(*)                  as ads,
        sum(impressions)          as impressions,
        sum(clicks)               as clicks,
        sum(spend_usd)            as spend_usd,
        sum(conversions)          as conversions,
        sum(approved_conversions) as approved_conversions
    from ads
    group by campaign_id,age_band,gender
)

select
    *,
    {{ safe_divide('clicks', 'impressions') }}              as ctr,
    {{ safe_divide('spend_usd', 'clicks') }}                as cpc_usd,
    {{ safe_divide('spend_usd * 1000', 'impressions') }}    as cpm_usd,
    {{ safe_divide('spend_usd', 'approved_conversions') }}  as cost_per_approved_conversion_usd,
    {{ safe_divide('approved_conversions', 'conversions') }} as approval_rate
from rolled
