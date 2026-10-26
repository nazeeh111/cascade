-- Retrospective showcase selection only; never a forecasting feature or model choice.
-- Grain: held-out UTC day; weighted actual next2h label rate (overlapping windows).
select cast(f.cutoff as date) as day,
 sum(f.target_late_n)::double/nullif(sum(f.target_n),0) as actual_network_rate,
 count(*) as airport_hours,sum(f.target_n) as overlapping_departure_denominator
from features f join predictions p on f.airport=p.airport and f.cutoff=p.cutoff
where p.model=? and p.split='test' and f.target_rate is not null
group by 1 order by actual_network_rate,day
