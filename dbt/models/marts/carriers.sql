-- Grain carrier. WN is forecast scope; other reporting codes occur only in January benchmark.
select distinct carrier,case when carrier='WN' then 'Southwest Airlines' else carrier||' (BTS reporting code)' end as name
from {{ source('public_snapshot','raw_carrier_cohorts') }}
union select 'WN','Southwest Airlines'
