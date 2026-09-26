-- A user sampled by several seeds must carry identical treatment and outcomes
-- in every file, and every visit-file user must exist in the conversion file.
with v as (
    select criteo_row_id, count(distinct treatment) nt, count(distinct visit) ny
    from {{ ref('stg_criteo__visit_outcomes') }} group by 1
),
c as (
    select criteo_row_id, count(distinct treatment) nt, count(distinct conversion) ny
    from {{ ref('stg_criteo__conversion_outcomes') }} group by 1
),
cross_file as (
    select v1.criteo_row_id
    from {{ ref('stg_criteo__visit_outcomes') }} v1
    join {{ ref('stg_criteo__conversion_outcomes') }} c1
      on v1.criteo_row_id = c1.criteo_row_id and v1.sample_seed = c1.sample_seed
    where v1.treatment <> c1.treatment
)
select 'visit_file_conflict' as issue, criteo_row_id from v where nt > 1 or ny > 1
union all
select 'conversion_file_conflict', criteo_row_id from c where nt > 1 or ny > 1
union all
select 'treatment_mismatch_across_files', criteo_row_id from cross_file
union all
select 'missing_from_conversion_file', v.criteo_row_id
from v left join c using (criteo_row_id) where c.criteo_row_id is null
