-- Grain airport/cutoff. 60-min weather and 15-min departure publication assumptions.
with weather_join as (
 select c.*,w.temp_c,w.wind_ms,w.visibility_m,
   date_diff('minute',w.observed_at,c.cutoff) as weather_age_min,
   w.available_at as weather_available_at,w.observation_hash as weather_observation_hash
 from {{ ref('int_cutoff_features') }} c asof left join {{ ref('stg_weather') }} w
 on c.airport=w.airport and c.cutoff>=w.available_at
), upstream as (
 select c.airport,c.cutoff,
  sum(e.inbound_weight*coalesce(u.lag_rate_2h,0)) as upstream_rate
 from {{ ref('int_cutoff_features') }} c left join {{ ref('network_edges') }} e on c.airport=e.dest
 left join {{ ref('int_cutoff_features') }} u on e.origin=u.airport and c.cutoff=u.cutoff
 group by 1,2
)
select w.* exclude(temp_c,wind_ms,visibility_m),
 case when weather_age_min<=180 then temp_c end as temp_c,
 case when weather_age_min<=180 then wind_ms end as wind_ms,
 case when weather_age_min<=180 then visibility_m end as visibility_m,
 coalesce(u.upstream_rate,0) as upstream_rate
from weather_join w join upstream u using(airport,cutoff)
where cutoff >= (select min(cutoff)+interval '48 hours' from {{ ref('int_airport_hours') }})
