-- Grain directed origin/dest. Frozen training-period schedule weights (Jan-Jun only).
with counts as (
 select f.origin,f.dest,count(*) as flights
 from {{ ref('flights') }} f join {{ ref('airports') }} a on f.origin=a.airport and a.focal
 join {{ ref('airports') }} b on f.dest=b.airport and b.focal
 where sched_dep<timestamp '2023-07-01' group by 1,2
)
select *, flights::double/sum(flights) over(partition by dest) as inbound_weight from counts
