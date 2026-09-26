-- Campaign and segment rollups must sum back to ad-grain totals.
with ad as (
    select sum(impressions) i, sum(clicks) c, sum(spend_usd) s, sum(approved_conversions) a
    from {{ ref('fct_ad_performance') }}
),
r as (
    select 'campaign' as rollup, sum(impressions) i, sum(clicks) c, sum(spend_usd) s, sum(approved_conversions) a
    from {{ ref('agg_campaign_performance') }}
    union all
    select 'segment', sum(impressions), sum(clicks), sum(spend_usd), sum(approved_conversions)
    from {{ ref('agg_campaign_segment_performance') }}
)
select r.* from r cross join ad
where r.i <> ad.i or r.c <> ad.c or abs(r.s - ad.s) > 0.005 or r.a <> ad.a
