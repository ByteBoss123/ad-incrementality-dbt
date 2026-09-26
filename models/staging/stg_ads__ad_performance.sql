-- One row per ad. Spend arrives as float strings with float noise
-- (e.g. 1.429999948); rounded to cents here so downstream sums reconcile.
with source as (
    select * from {{ source('raw_ads', 'KAG_conversion_data') }}
),

renamed as (
    select
        cast(ad_id as bigint)                           as ad_id,
        cast(xyz_campaign_id as integer)                as campaign_id,
        cast(fb_campaign_id as bigint)                  as ad_set_id,
        trim(age)                                       as age_band,
        upper(trim(gender))                             as gender,
        cast(interest as integer)                       as interest_code,
        cast(Impressions as bigint)                     as impressions,
        cast(Clicks as integer)                         as clicks,
        round(cast(Spent as double), 2)                 as spend_usd,
        cast(Total_Conversion as integer)               as conversions,
        cast(Approved_Conversion as integer)            as approved_conversions
    from source
)

select * from renamed
