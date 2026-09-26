-- One row per Criteo user: treatment assignment plus both outcomes.
-- Users sampled by more than one seed collapse to a single row; the singular
-- test assert_criteo_duplicates_agree proves their values never disagree.
with visits as (
    select criteo_row_id, max(treatment) as treatment, max(visit) as visit,
           count(*) as samples_containing_user
    from {{ ref('stg_criteo__visit_outcomes') }}
    group by criteo_row_id
),

conversions as (
    select criteo_row_id, max(conversion) as conversion
    from {{ ref('stg_criteo__conversion_outcomes') }}
    group by criteo_row_id
)

select
    v.criteo_row_id,
    v.treatment = 1               as is_treatment,
    v.visit,
    c.conversion,
    v.samples_containing_user
from visits v
inner join conversions c on v.criteo_row_id = c.criteo_row_id
