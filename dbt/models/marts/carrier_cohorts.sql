-- Grain carrier/airport/period. One-month benchmark makes carrier selection visible.
select *, disrupted_n::double/nullif(scheduled_n-unknown_n,0) as disruption_rate
from {{ source('public_snapshot','raw_carrier_cohorts') }}
