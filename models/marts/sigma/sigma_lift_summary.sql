-- BI-facing incrementality table for the Sigma workbook: one row per outcome,
-- rates already in percentage points so Sigma needs no calculated columns.
with lift as (select * from {{ ref('fct_campaign_lift') }}),
power as (select outcome, mde_abs, mde_rel from {{ ref('fct_experiment_power') }})

select
    l.outcome,
    l.t_users                           as targeted_users,
    l.c_users                           as control_users,
    l.t_cvr                             as targeted_rate,
    l.c_cvr                             as control_rate,
    l.abs_lift * 100                    as abs_lift_pp,
    l.abs_lift_ci95_low * 100           as ci95_low_pp,
    l.abs_lift_ci95_high * 100          as ci95_high_pp,
    l.rel_lift                          as relative_lift,
    l.z_stat,
    l.is_significant_95,
    l.incremental_conversions           as incremental_outcomes,
    p.mde_abs * 100                     as mde_pp,
    p.mde_rel                           as mde_relative
from lift l
join power p on l.outcome = p.outcome
