-- Grain: airport/cutoff for a declared held-out UTC date and selected frozen model.
-- Parameters: model, day_start, day_end. Predictions retain their original model run.
select f.airport,f.cutoff,f.target_n as scheduled,f.lag_rate_2h as observed_rate,
 p.prediction,f.target_rate,f.backlog_n as backlog,f.temp_c,f.wind_ms,f.visibility_m,
 f.weather_age_min,f.weather_available_at,f.max_event_available_at,f.label_available_at
from features f left join predictions p on f.airport=p.airport and f.cutoff=p.cutoff
 and p.model=? and p.split='test'
where f.cutoff>=? and f.cutoff<? order by f.cutoff,f.airport
