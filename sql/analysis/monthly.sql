-- Q: Is the focal network representative of all reported WN flights through the year?
with cohorts as (
select f.source_month, a.focal, count(*) as n,
 sum(cancelled::int) as cancelled_n,
 count(*) filter(where dep_delay>=15 or cancelled) as disrupted_n,
 count(*) filter(where dep_delay is null and not cancelled) as unknown_n,
 avg(dep_delay) as mean_departure_minutes,
 quantile_cont(dep_delay,.99) as p99_departure_minutes
from flights f join airports a on f.origin=a.airport
group by 1,2
), rates as (
 select *, disrupted_n::double/nullif(n-unknown_n,0) as disruption_rate from cohorts
)
select *,lag(disruption_rate) over(partition by focal order by source_month) as previous_month_rate,
 disruption_rate-lag(disruption_rate) over(partition by focal order by source_month) as month_rate_change
from rates order by source_month,focal
