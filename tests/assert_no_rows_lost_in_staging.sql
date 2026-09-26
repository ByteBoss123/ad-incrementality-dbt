-- Staging unions must carry every source row.
{% set checks = [] %}
{% for o in ['visit', 'conversion'] %}
select '{{ o }}' as outcome,
       ({% for s in [42, 43, 44] %}(select count(*) from {{ source('criteo', o ~ '_frac0.1_seed' ~ s) }}){% if not loop.last %} + {% endif %}{% endfor %}) as source_rows,
       (select count(*) from {{ ref('stg_criteo__' ~ o ~ '_outcomes') }}) as stg_rows
where ({% for s in [42, 43, 44] %}(select count(*) from {{ source('criteo', o ~ '_frac0.1_seed' ~ s) }}){% if not loop.last %} + {% endif %}{% endfor %})
   <> (select count(*) from {{ ref('stg_criteo__' ~ o ~ '_outcomes') }})
{% if not loop.last %}union all{% endif %}
{% endfor %}
union all
select 'ads', (select count(*) from {{ source('raw_ads', 'KAG_conversion_data') }}),
       (select count(*) from {{ ref('stg_ads__ad_performance') }})
where (select count(*) from {{ source('raw_ads', 'KAG_conversion_data') }}) <> (select count(*) from {{ ref('stg_ads__ad_performance') }})
