-- LAG/LEAD is retrospective ONLY: final actual aircraft assignments are not knowable forecasts.
with ordered as (
 select flight_id as from_flight_id, tail, dest as airport, sched_arr,actual_arr,arr_delay as inbound_arr_delay,
  lead(flight_id) over w as to_flight_id,lead(origin) over w as next_origin,
  lead(sched_dep) over w as next_sched_dep,lead(actual_dep) over w as next_actual_dep,
  lead(dep_delay) over w as outbound_dep_delay,
  arrival_inconsistent or scheduled_arr_clock_inconsistent or actual_dep_clock_inconsistent as time_inconsistent,
  lead(arrival_inconsistent or scheduled_arr_clock_inconsistent or actual_dep_clock_inconsistent) over w as next_time_inconsistent,
  cancelled,diverted,lead(cancelled) over w as next_cancelled,lead(diverted) over w as next_diverted
 from {{ ref('flights') }} where tail is not null
 window w as (partition by carrier,tail order by sched_dep,flight_id)
)
select *, date_diff('minute',sched_arr,next_sched_dep) as sched_gap_min,
 date_diff('minute',actual_arr,next_actual_dep) as actual_gap_min,
 case when time_inconsistent or next_time_inconsistent then 'inconsistent_source_timestamps'
   when airport<>next_origin then 'discontinuous_airport'
   when cancelled or next_cancelled then 'cancelled'
   when diverted or next_diverted then 'diverted'
   when actual_arr is null or next_actual_dep is null then 'missing_actual'
   when date_diff('minute',sched_arr,next_sched_dep) not between 20 and 360 then 'scheduled_gap'
   when actual_arr>next_actual_dep then 'actual_overlap'
   else 'valid' end as rotation_quality
from ordered where to_flight_id is not null
