select from_flight_id from {{ ref('rotations') }}
where sched_gap_min not between 20 and 360 or actual_gap_min<0 or tail is null
