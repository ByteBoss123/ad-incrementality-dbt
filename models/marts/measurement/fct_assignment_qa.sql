-- Sample-ratio check input: observed treatment share per sample vs the 85/15
-- design documented for the Criteo release. The chi-square SRM p-value is
-- computed in validation/validate.py.
with v as (select * from {{ ref('stg_criteo__visit_outcomes') }})

select
    sample_seed,
    count(*)                                   as users,
    sum(treatment)                             as t_users,
    count(*) - sum(treatment)                  as c_users,
    {{ safe_divide('sum(treatment)', 'count(*)') }}                       as t_share,
    {{ var('design_treatment_share') }}                                   as design_t_share,
    {{ safe_divide('sum(treatment)', 'count(*)') }} - {{ var('design_treatment_share') }} as share_gap
from v
group by sample_seed
