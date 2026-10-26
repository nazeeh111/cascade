-- Actual departure available 15 minutes after event, then bucket to first hourly cutoff.
select origin as airport,
 date_trunc('hour',actual_dep+interval '15 minutes')+
   case when actual_dep+interval '15 minutes'=date_trunc('hour',actual_dep+interval '15 minutes')
        then interval '0 hours' else interval '1 hour' end as event_hour,
 count(*) as observed_n, count(*) filter(where dep_delay>=15) as observed_late_n,
 max(actual_dep+interval '15 minutes') as max_available_at
from {{ ref('flights') }} f join {{ ref('airports') }} a on f.origin=a.airport and a.focal
where not cancelled and actual_dep is not null group by 1,2
