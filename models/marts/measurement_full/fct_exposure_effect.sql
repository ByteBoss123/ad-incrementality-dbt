-- Effect per exposed user. Not every targeted user actually saw an ad (exposure = 1),
-- and control users cannot be exposed. Under that one-sided non-compliance, the
-- Wald / complier-average effect is the intent-to-treat lift divided by the exposure
-- rate in the treated arm. The naive exposed-vs-control comparison is reported
-- alongside it and is NOT causal (exposure depends on user activity).
with u as (select * from {{ ref('stg_criteo__full_release') }}),
arms as (
    select
        sum(case when is_treatment then 1 else 0 end)                         as t_users,
        sum(case when is_treatment then exposure else 0 end)                  as t_exposed,
        sum(case when not is_treatment then exposure else 0 end)              as c_exposed,
        avg(case when is_treatment then visit end)                            as t_visit,
        avg(case when not is_treatment then visit end)                        as c_visit,
        avg(case when is_treatment then conversion end)                       as t_conv,
        avg(case when not is_treatment then conversion end)                   as c_conv,
        avg(case when is_treatment and exposure = 1 then conversion end)      as exposed_conv,
        avg(case when is_treatment and exposure = 1 then visit end)           as exposed_visit
    from u
)
select
    t_users,
    t_exposed,
    c_exposed,
    {{ safe_divide('t_exposed', 't_users') }}                       as exposure_rate,
    t_visit - c_visit                                               as itt_visit,
    t_conv - c_conv                                                 as itt_conversion,
    {{ safe_divide('t_visit - c_visit', safe_divide('t_exposed', 't_users')) }} as cace_visit,
    {{ safe_divide('t_conv - c_conv', safe_divide('t_exposed', 't_users')) }}   as cace_conversion,
    exposed_visit - c_visit                                         as naive_exposed_vs_control_visit,
    exposed_conv - c_conv                                           as naive_exposed_vs_control_conversion
from arms
