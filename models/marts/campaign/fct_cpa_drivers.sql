-- Driver decomposition of cost per approved conversion (CPA).
-- CPA = CPC x clicks per approved conversion, exactly. So the log gap between a
-- campaign's CPA and the best (lowest-CPA) campaign's CPA splits additively into
-- a click-cost part and a click-to-conversion part. Shares sum to 1.
with c as (
    select
        campaign_id,
        spend_usd,
        clicks,
        approved_conversions,
        {{ safe_divide('spend_usd', 'clicks') }}               as cpc_usd,
        {{ safe_divide('clicks', 'approved_conversions') }}    as clicks_per_approved_conversion,
        {{ safe_divide('spend_usd', 'approved_conversions') }} as cpa_usd
    from {{ ref('agg_campaign_performance') }}
),
best as (
    select cpc_usd as best_cpc, clicks_per_approved_conversion as best_cpac, cpa_usd as best_cpa
    from c
    order by cpa_usd
    limit 1
)
select
    c.*,
    {{ safe_divide('c.cpa_usd', 'b.best_cpa') }} as cpa_ratio_vs_best,
    case when c.cpa_usd > b.best_cpa then
        {{ safe_divide('ln(' ~ safe_divide('c.cpc_usd', 'b.best_cpc') ~ ')',
                       'ln(' ~ safe_divide('c.cpa_usd', 'b.best_cpa') ~ ')') }}
    end as cpc_share_of_gap,
    case when c.cpa_usd > b.best_cpa then
        {{ safe_divide('ln(' ~ safe_divide('c.clicks_per_approved_conversion', 'b.best_cpac') ~ ')',
                       'ln(' ~ safe_divide('c.cpa_usd', 'b.best_cpa') ~ ')') }}
    end as conversion_rate_share_of_gap
from c
cross join best b
