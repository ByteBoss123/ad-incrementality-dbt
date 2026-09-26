-- Ad-grain performance fact with standard paid-media efficiency metrics.
with ads as (
    select * from {{ ref('stg_ads__ad_performance') }}
)

select
    ad_id,
    campaign_id,
    ad_set_id,
    age_band,
    gender,
    interest_code,
    impressions,
    clicks,
    spend_usd,
    conversions,
    approved_conversions,
    {{ safe_divide('clicks', 'impressions') }}              as ctr,
    {{ safe_divide('spend_usd', 'clicks') }}                as cpc_usd,
    {{ safe_divide('spend_usd * 1000', 'impressions') }}    as cpm_usd,
    {{ safe_divide('spend_usd', 'approved_conversions') }}  as cost_per_approved_conversion_usd,
    {{ safe_divide('approved_conversions', 'conversions') }} as approval_rate
from ads
