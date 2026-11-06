-- Every user in the three UpliftBench samples must appear in the full release at the same
-- row position with the same treatment and outcomes. Proves the samples' provenance.
with v as (select * from {{ ref('stg_criteo__visit_outcomes') }}),
c as (select * from {{ ref('stg_criteo__conversion_outcomes') }}),
f as (select * from {{ ref('stg_criteo__full_release') }})
select 'visit' as outcome, v.criteo_row_id
from v left join f on f.criteo_row_id = v.criteo_row_id
where f.criteo_row_id is null or (v.treatment = 1) <> f.is_treatment or v.visit <> f.visit
union all
select 'conversion', c.criteo_row_id
from c left join f on f.criteo_row_id = c.criteo_row_id
where f.criteo_row_id is null or (c.treatment = 1) <> f.is_treatment or c.conversion <> f.conversion
