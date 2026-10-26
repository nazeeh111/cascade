-- Grain from_flight_id/to_flight_id; validated but potentially incomplete domestic-only chain.
select from_flight_id,to_flight_id,tail,airport,sched_gap_min,actual_gap_min,inbound_arr_delay,outbound_dep_delay
from {{ ref('int_rotations') }} where rotation_quality='valid'
