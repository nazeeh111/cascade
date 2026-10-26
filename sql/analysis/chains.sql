-- Q: Which retrospective paths show plausible propagation through validated tail continuity?
-- Finite three-leg paths with destination continuity and growing/remaining delays.
select f.flight_date,f.tail,f.flight_id as flight1,m.flight_id as flight2,z.flight_id as flight3,
 f.origin||' → '||f.dest||' → '||m.dest||' → '||z.dest as path,
 f.dep_delay as dep1,f.arr_delay as arr1,m.dep_delay as dep2,m.arr_delay as arr2,z.dep_delay as dep3,
 r1.sched_gap_min as turn1,r2.sched_gap_min as turn2
from rotations r1 join rotations r2 on r1.to_flight_id=r2.from_flight_id
join flights f on f.flight_id=r1.from_flight_id
join flights m on m.flight_id=r1.to_flight_id
join flights z on z.flight_id=r2.to_flight_id
where f.flight_date>=date '2023-10-01' and f.arr_delay>=30 and m.dep_delay>=30 and z.dep_delay>=30
order by f.arr_delay desc,f.flight_id limit 20
