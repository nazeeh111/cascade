select c.airport,c.cutoff,w.observed_at,w.temp_c,w.wind_ms,w.visibility_m
from (select * from int_airport_hours where cutoff>=timestamp '2023-01-01'
and cutoff<timestamp '2023-02-01') c
asof left join stg_weather w on c.airport=w.airport and c.cutoff>=w.available_at
order by c.airport,c.cutoff;
