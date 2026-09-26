-- Funnel view: conversion rate among users who visited, by arm.
-- NOT randomized: visiting happens after assignment, so the visitor pools in
-- each arm can differ. Descriptive only; use fct_campaign_lift for causal claims.
with users as (select * from {{ ref('int_criteo__users') }})

select
    case when is_treatment then 'treatment' else 'control' end as arm,
    count(*)                                   as users,
    sum(visit)                                 as visitors,
    sum(conversion)                            as converters,
    {{ safe_divide('sum(visit)', 'count(*)') }}        as visit_rate,
    {{ safe_divide('sum(conversion)', 'sum(visit)') }} as conversion_per_visitor
from users
group by 1
