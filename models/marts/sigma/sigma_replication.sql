-- BI-facing replication view: lift per independent random sample.
select
    outcome,
    cast(sample_seed as varchar) as sample_id,
    t_users                      as targeted_users,
    c_users                      as control_users,
    rel_lift                     as relative_lift,
    abs_lift * 100               as abs_lift_pp,
    is_significant_95
from {{ ref('fct_lift_by_sample') }}
