-- Headline incrementality readout on the full 13.98M-user release, one row per outcome.
with users as (select * from {{ ref('stg_criteo__full_release') }}),

counts as (
    {% for outcome in ['visit', 'conversion'] %}
    select
        '{{ outcome }}' as outcome,
        sum(case when is_treatment then 1 else 0 end)                 as t_users,
        sum(case when is_treatment then {{ outcome }} else 0 end)     as t_conv,
        sum(case when not is_treatment then 1 else 0 end)             as c_users,
        sum(case when not is_treatment then {{ outcome }} else 0 end) as c_conv
    from users
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

{{ lift_from_counts('counts', ['outcome']) }}
