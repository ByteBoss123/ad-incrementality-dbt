-- One row per (sample, user) for the conversion outcome. The three samples overlap,
-- so a user can appear more than once here; de-duplication happens downstream.
{% set seeds = [42, 43, 44] %}
{% for s in seeds %}
select
    cast(row_id as bigint) as criteo_row_id,
    {{ s }}                as sample_seed,
    cast(w as integer)     as treatment,
    cast(y as integer)     as conversion
from {{ source('criteo', 'conversion_frac0.1_seed' ~ s) }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
