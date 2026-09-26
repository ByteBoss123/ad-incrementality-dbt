{#
  lift_from_counts(counts_cte, group_cols)
  Input CTE must expose: <group_cols>, t_users, t_conv, c_users, c_conv.
  Returns two-proportion lift statistics per group:
    rates, absolute lift, relative lift, unpooled 95% CI on absolute lift,
    pooled z statistic, and incremental conversions among treated users.
  Slices with fewer than var('min_conversions_per_arm') conversions in either
  arm are marked is_readable = false and never flagged significant, because the
  normal approximation breaks down (e.g. a control arm with 0 conversions).
  p-values are computed in validation/validate.py because a normal CDF is not
  portable between DuckDB and Snowflake SQL.
#}
{% macro lift_from_counts(counts_cte, group_cols=[]) -%}
rates as (
    select
        *,
        {{ safe_divide('t_conv', 't_users') }} as t_cvr,
        {{ safe_divide('c_conv', 'c_users') }} as c_cvr,
        {{ safe_divide('t_conv + c_conv', 't_users + c_users') }} as pooled_cvr
    from {{ counts_cte }}
),

stats as (
    select
        *,
        t_cvr - c_cvr as abs_lift,
        {{ safe_divide('t_cvr - c_cvr', 'c_cvr') }} as rel_lift,
        sqrt(t_cvr * (1 - t_cvr) / nullif(cast(t_users as double), 0)
           + c_cvr * (1 - c_cvr) / nullif(cast(c_users as double), 0)) as se_unpooled,
        sqrt(pooled_cvr * (1 - pooled_cvr)
           * (cast(1 as double) / nullif(t_users, 0) + cast(1 as double) / nullif(c_users, 0))) as se_pooled
    from rates
)

select
    {% for c in group_cols %}{{ c }},
    {% endfor -%}
    t_users,
    t_conv,
    c_users,
    c_conv,
    t_cvr,
    c_cvr,
    abs_lift,
    rel_lift,
    abs_lift - {{ var('z_crit_95') }} * se_unpooled as abs_lift_ci95_low,
    abs_lift + {{ var('z_crit_95') }} * se_unpooled as abs_lift_ci95_high,
    {{ safe_divide('abs_lift', 'se_pooled') }}     as z_stat,
    (t_conv >= {{ var('min_conversions_per_arm') }}
        and c_conv >= {{ var('min_conversions_per_arm') }})       as is_readable,
    (t_conv >= {{ var('min_conversions_per_arm') }}
        and c_conv >= {{ var('min_conversions_per_arm') }}
        and abs({{ safe_divide('abs_lift', 'se_pooled') }}) >= {{ var('z_crit_95') }}) as is_significant_95,
    abs_lift * t_users                              as incremental_conversions
from stats
{%- endmacro %}
