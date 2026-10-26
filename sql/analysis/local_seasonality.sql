-- Q: How do local departure hour, weekday, and season change disruption?
with cohorts as (
 select extract(hour from timezone(origin_tz,timezone('UTC',sched_dep)))::int as local_hour,
 dayofweek(flight_date) as weekday,month(flight_date) as month,
 cancelled,dep_delay
 from flights f join airports a on f.origin=a.airport and a.focal
)
select local_hour,weekday,month,count(*) as n,
 count(*) filter(where dep_delay>=15 or cancelled) as disrupted_n,
 count(*) filter(where dep_delay is null and not cancelled) as unknown_n
from cohorts group by 1,2,3 order by 1,2,3
