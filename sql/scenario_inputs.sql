-- Exact query executed by cascade/simulation.py; parameters cutoff−12h and cutoff+8h.
-- Retrospective actual-tail topology, not a cutoff-safe forecast feature query.
SELECT f.flight_id,f.origin,f.dest,f.sched_dep,f.sched_arr,f.actual_dep,f.observed_gate_out,f.actual_arr,f.dep_delay,f.arr_delay,f.cancelled,f.diverted,
            extract(hour FROM timezone(f.origin_tz, timezone('UTC',f.sched_dep)))::INTEGER AS local_hour,
            r.from_flight_id,r.sched_gap_min,p.actual_arr AS prev_actual_arr,p.arr_delay AS prev_arr_delay,
            p.sched_dep as prev_sched_dep,p.actual_dep as prev_actual_dep,p.dep_delay as prev_dep_delay,
            p.origin as prev_origin,
            extract(hour from timezone(p.origin_tz,timezone('UTC',p.sched_dep)))::integer as prev_local_hour
            FROM flights f LEFT JOIN rotations r ON r.to_flight_id=f.flight_id
            LEFT JOIN flights p ON p.flight_id=r.from_flight_id
            WHERE f.sched_dep >= ? AND f.sched_dep < ? ORDER BY f.sched_dep,f.flight_id;
