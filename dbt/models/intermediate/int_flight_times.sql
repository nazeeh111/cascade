-- Grain flight_id. BTS 2400 is next-day midnight; scheduled elapsed fixes destination day.
with local as (
 select f.*, a.timezone as origin_tz, b.timezone as dest_tz,
   cast(flight_date as timestamp) + (dep_clock//100*60 + dep_clock%100) * interval '1 minute' as dep_local
 from {{ ref('stg_flights') }} f
 left join {{ ref('airports') }} a on f.origin=a.airport
 left join {{ ref('airports') }} b on f.dest=b.airport
), utc as (
 select *, cast(timezone(origin_tz,dep_local) as timestamp) as sched_dep
 from local
), all_times as (
 select *, sched_dep + scheduled_elapsed_min * interval '1 minute' as sched_arr,
    sched_dep+dep_delay*interval '1 minute' as observed_gate_out,
    case when not cancelled then sched_dep+dep_delay*interval '1 minute' end as actual_dep,
    case when not cancelled and not diverted then sched_dep+dep_delay*interval '1 minute'
       + actual_elapsed_min*interval '1 minute' end as actual_arr,
    case
      when origin_tz is null or dest_tz is null then 'missing_timezone'
      when dep_clock is null or dep_clock<0 or dep_clock>2400 or dep_clock%100>=60 then 'invalid_clock'
      when timezone(origin_tz,timezone('UTC',sched_dep))<>dep_local then 'dst_gap'
      when timezone(origin_tz,timezone('UTC',sched_dep-interval '1 hour'))=dep_local
        or timezone(origin_tz,timezone('UTC',sched_dep+interval '1 hour'))=dep_local then 'dst_fold'
      when scheduled_elapsed_min is null or scheduled_elapsed_min<=0 then 'missing_elapsed'
      else 'valid' end as time_quality
 from utc
)
select *,
 case when actual_arr is not null and arr_delay is not null then
  abs(date_diff('minute',sched_arr,actual_arr)-arr_delay)>1 else false end as arrival_inconsistent,
 case when sched_arr is not null and dest_tz is not null then
   (hour(timezone(dest_tz,timezone('UTC',sched_arr)))*60+minute(timezone(dest_tz,timezone('UTC',sched_arr))))
     <> ((arr_clock//100*60+arr_clock%100)%1440) else false end as scheduled_arr_clock_inconsistent,
 case when observed_gate_out is not null and actual_dep_clock is not null then
   (hour(timezone(origin_tz,timezone('UTC',observed_gate_out)))*60+minute(timezone(origin_tz,timezone('UTC',observed_gate_out))))
     <> ((actual_dep_clock//100*60+actual_dep_clock%100)%1440) else false end as actual_dep_clock_inconsistent
from all_times
