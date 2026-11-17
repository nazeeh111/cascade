-- Retrospective adjacency from the discontinuous bundled sample, not causal propagation.
select r.tail, r.airport, a.flight_date, a.origin inbound_origin, a.dest inbound_dest,
 a.sched_arr inbound_scheduled_arrival_utc, a.actual_arr inbound_actual_arrival_utc,
 b.flight_number outbound_flight, b.dest outbound_dest,
 b.sched_dep outbound_scheduled_departure_utc, b.actual_dep outbound_actual_departure_utc,
 r.sched_gap_min, r.actual_gap_min, r.inbound_arr_delay, r.outbound_dep_delay
from rotations r join flights a on a.flight_id=r.from_flight_id
join flights b on b.flight_id=r.to_flight_id
where a.flight_date=date '2023-01-01' and r.inbound_arr_delay>=60 and r.outbound_dep_delay>=15
order by r.inbound_arr_delay desc, r.tail, b.flight_number limit 1;
