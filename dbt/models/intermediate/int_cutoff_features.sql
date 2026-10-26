-- Schedule assumed known before cutoff. Final BTS files are not historical schedule snapshots.
with scheduled as (
 select origin as airport,date_trunc('hour',sched_dep) as h,count(*) as n,
   count(*) filter(where dep_delay>=15 or cancelled) as late_n,
   count(*) filter(where dep_delay is null and not cancelled) as unknown_n,
   max(observed_gate_out+interval '15 minutes') as last_label
 from {{ ref('flights') }} group by 1,2
), backlog as (
 select f.origin as airport,h.cutoff,count(*) as backlog_n
 from {{ ref('flights') }} f join {{ ref('airports') }} a on f.origin=a.airport and a.focal,
 lateral generate_series(date_trunc('hour',sched_dep+interval '15 minutes')+
   case when sched_dep+interval '15 minutes'=date_trunc('hour',sched_dep+interval '15 minutes')
        then interval '0 hours' else interval '1 hour' end,
   date_trunc('hour',sched_dep+interval '6 hours'),interval '1 hour') h(cutoff)
 where observed_gate_out is null or actual_dep_clock_inconsistent or observed_gate_out+interval '15 minutes'>h.cutoff
 group by 1,2
), history as (
 select g.*,coalesce(e.observed_n,0) as obs_n,coalesce(e.observed_late_n,0) as obs_late,
 e.max_available_at,
 sum(coalesce(e.observed_n,0)) over w2 as observed_n_2h,
 sum(coalesce(e.observed_late_n,0)) over w2 as late_n_2h,
 sum(coalesce(e.observed_n,0)) over w6 as observed_n_6h,
 sum(coalesce(e.observed_late_n,0)) over w6 as late_n_6h,
 max(e.max_available_at) over w6 as max_event_available_at
 from {{ ref('int_airport_hours') }} g left join {{ ref('int_hourly_events') }} e
 on g.airport=e.airport and g.cutoff=e.event_hour
 window w2 as(partition by g.airport order by g.cutoff rows between 1 preceding and current row),
 w6 as(partition by g.airport order by g.cutoff rows between 5 preceding and current row)
)
select h.airport,h.cutoff,coalesce(s1.n,0)+coalesce(s2.n,0) as target_n,
 coalesce(s1.late_n,0)+coalesce(s2.late_n,0) as target_late_n,
 case when coalesce(s1.unknown_n,0)+coalesce(s2.unknown_n,0)=0 then
 (coalesce(s1.late_n,0)+coalesce(s2.late_n,0))::double/nullif(coalesce(s1.n,0)+coalesce(s2.n,0),0) end as target_rate,
 coalesce(s1.unknown_n,0)+coalesce(s2.unknown_n,0) as target_unknown_n,
 greatest(h.cutoff+interval '14 hours',s1.last_label,s2.last_label) as label_available_at,
 coalesce(s1.n,0)+coalesce(s2.n,0) as sched_n_2h,
 hour(timezone(a.timezone,timezone('UTC',h.cutoff))) as hour,
 dayofweek(timezone(a.timezone,timezone('UTC',h.cutoff))) as dow,
 month(timezone(a.timezone,timezone('UTC',h.cutoff))) as month,
 late_n_2h::double/nullif(observed_n_2h,0) as lag_rate_2h,
 late_n_6h::double/nullif(observed_n_6h,0) as lag_rate_6h,
 observed_n_2h,coalesce(b.backlog_n,0) as backlog_n,h.max_event_available_at
from history h join {{ ref('airports') }} a on h.airport=a.airport
left join scheduled s1 on h.airport=s1.airport and h.cutoff=s1.h
left join scheduled s2 on h.airport=s2.airport and h.cutoff+interval '1 hour'=s2.h
left join backlog b on h.airport=b.airport and h.cutoff=b.cutoff
