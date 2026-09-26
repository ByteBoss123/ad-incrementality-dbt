-- Replication check: the same lift computed separately on each of the three
-- independent random samples. Stable estimates across samples mean the
-- headline is not an artifact of one draw.
with v as (select * from {{ ref('stg_criteo__visit_outcomes') }}),
c as (select * from {{ ref('stg_criteo__conversion_outcomes') }}),

counts as (
    select
        'visit' as outcome, sample_seed,
        sum(treatment) as t_users,
        sum(case when treatment = 1 then visit else 0 end) as t_conv,
        sum(1 - treatment) as c_users,
        sum(case when treatment = 0 then visit else 0 end) as c_conv
    from v group by sample_seed
    union all
    select
        'conversion', sample_seed,
        sum(treatment),
        sum(case when treatment = 1 then conversion else 0 end),
        sum(1 - treatment),
        sum(case when treatment = 0 then conversion else 0 end)
    from c group by sample_seed
),

{{ lift_from_counts('counts', ['outcome', 'sample_seed']) }}
