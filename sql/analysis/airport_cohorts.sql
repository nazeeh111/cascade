-- Q: Which focal airports carry the highest observed disruption rate?
select origin as airport,count(*) as n,
 count(*) filter(where dep_delay>=15 or cancelled) as disrupted_n,
 sum(cancelled::int) as cancelled_n,
 count(*) filter(where dep_delay is null and not cancelled) as unknown_n,
 avg(dep_delay) as mean_dep_delay,
 count(*) filter(where arr_delay is null) as missing_arr_n
from flights f join airports a on f.origin=a.airport and a.focal
group by 1 order by disrupted_n::double/n desc
