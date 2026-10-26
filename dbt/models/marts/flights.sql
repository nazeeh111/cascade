-- Grain: flight_id. Quarantined DST/correction/clock records remain in int_flight_times.
select * from {{ ref('int_flight_times') }} where time_quality='valid' and revision_n=1
