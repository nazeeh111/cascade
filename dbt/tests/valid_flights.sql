select flight_id from {{ ref('flights') }}
where time_quality<>'valid' or sched_arr<=sched_dep
 or (cancelled and actual_dep is not null) or (diverted and actual_arr is not null)
 or (actual_arr<actual_dep) or revision_n<>1
