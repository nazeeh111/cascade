-- Dense UTC hour grid. First 48h excluded downstream to avoid snapshot-left-boundary history.
with extent as (
 select greatest(timestamp '2023-01-01',date_trunc('day',min(sched_dep))) as first_hour,
   least(timestamp '2024-01-01',date_trunc('day',max(sched_dep))) as last_hour from {{ ref('flights') }}
)
select a.airport, h.cutoff from extent e,
 lateral generate_series(e.first_hour,e.last_hour-interval '2 hours',interval '1 hour') h(cutoff)
 cross join {{ ref('airports') }} a where a.focal
