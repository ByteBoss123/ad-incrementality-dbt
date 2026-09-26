-- Minimum detectable effect (absolute, two-sided alpha 0.05, 80% power) for each
-- outcome at the observed sample sizes and control rates. Tells a reader
-- whether a null result would have been informative.
with l as (select * from {{ ref('fct_campaign_lift') }})

select
    outcome,
    t_users,
    c_users,
    c_cvr,
    ({{ var('z_crit_95') }} + {{ var('z_power_80') }})
      * sqrt(c_cvr * (1 - c_cvr) * (cast(1 as double) / t_users + cast(1 as double) / c_users))      as mde_abs,
    ({{ var('z_crit_95') }} + {{ var('z_power_80') }})
      * sqrt(c_cvr * (1 - c_cvr) * (cast(1 as double) / t_users + cast(1 as double) / c_users)) / c_cvr as mde_rel,
    abs_lift,
    abs(abs_lift) >= ({{ var('z_crit_95') }} + {{ var('z_power_80') }})
      * sqrt(c_cvr * (1 - c_cvr) * (cast(1 as double) / t_users + cast(1 as double) / c_users))      as observed_lift_exceeds_mde
from l
