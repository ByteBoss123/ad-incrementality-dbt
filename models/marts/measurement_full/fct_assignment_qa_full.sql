-- Treatment share on the full release vs the 85/15 design (SRM p-value in validate.py).
select
    count(*)                                                   as users,
    sum(case when is_treatment then 1 else 0 end)              as t_users,
    sum(case when is_treatment then 0 else 1 end)              as c_users,
    {{ safe_divide('sum(case when is_treatment then 1 else 0 end)', 'count(*)') }} as t_share,
    {{ var('design_treatment_share') }}                        as design_t_share
from {{ ref('stg_criteo__full_release') }}
