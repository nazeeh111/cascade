-- Q: Is an observed late inbound associated with the next departure's delay?
select case when inbound_arr_delay>=15 then 'inbound_late15' else 'inbound_under15' end as cohort,
 count(*) as n, avg((outbound_dep_delay>=15)::int) as outbound_late_rate,
 avg(outbound_dep_delay) as mean_outbound_minutes,
 median(sched_gap_min) as median_scheduled_turn_minutes
from rotations where inbound_arr_delay is not null and outbound_dep_delay is not null
group by 1 order by 1
