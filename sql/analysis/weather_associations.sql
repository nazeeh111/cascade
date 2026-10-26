-- Q: How is disruption associated with the most recent available weather?
with matched as (
 select f.flight_id,f.cancelled,f.dep_delay,w.wind_ms,w.visibility_m,
 date_diff('minute',w.observed_at,f.sched_dep) as weather_age_min
 from flights f join airports a on f.origin=a.airport and a.focal
 asof left join stg_weather w on f.origin=w.airport and f.sched_dep>=w.available_at
), grouped as (
 select *,case when weather_age_min>180 or (wind_ms is null and visibility_m is null) then 'missing_or_stale'
  when visibility_m<3000 then 'visibility_below_3km'
  when wind_ms>=8 then 'wind_at_least_8mps' else 'other_observed' end as weather_group
 from matched
)
select weather_group,count(*) as n,
 count(*) filter(where dep_delay>=15 or cancelled) as disrupted_n,
 count(*) filter(where dep_delay is null and not cancelled) as unknown_n,
 avg(dep_delay) as mean_dep_delay
from grouped group by 1 order by 1
