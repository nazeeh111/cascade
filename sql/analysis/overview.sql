-- Q: What survives the source-to-analysis pipeline, and what is unobserved?
select count(*) as n, sum(cancelled::int) as cancelled_n,sum(diverted::int) as diverted_n,
 count(*) filter(where tail is null) as missing_tail_n,
 count(*) filter(where dep_delay is null) as missing_dep_delay_n,
 count(*) filter(where arr_delay is null) as missing_arr_delay_n,
 count(*) filter(where dep_delay<0) as early_departure_n,
 avg(dep_delay) as mean_dep_delay,median(dep_delay) as median_dep_delay,
 quantile_cont(dep_delay,.9) as p90_dep_delay,quantile_cont(dep_delay,.99) as p99_dep_delay,
 max(dep_delay) as max_dep_delay,
 count(*) filter(where arrival_inconsistent) as inconsistent_actual_arrival_n,
 count(*) filter(where scheduled_arr_clock_inconsistent) as inconsistent_scheduled_arrival_n,
 count(*) filter(where actual_dep_clock_inconsistent) as inconsistent_actual_departure_n
from flights
