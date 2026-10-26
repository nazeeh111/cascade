select flight_id,revision_n from {{ ref('stg_flights') }} where revision_n>1
