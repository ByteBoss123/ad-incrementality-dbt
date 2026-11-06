-- One row per user in the full Criteo Uplift v2.1 release.
select
    cast(row_id as bigint)     as criteo_row_id,
    cast(treatment as integer) = 1 as is_treatment,
    cast(visit as integer)      as visit,
    cast(conversion as integer) as conversion,
    cast(exposure as integer)   as exposure
from {{ source('criteo_full', 'criteo_uplift_v2.1') }}
