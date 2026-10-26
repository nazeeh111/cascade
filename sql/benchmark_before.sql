select c.airport,c.cutoff,w.observed_at,w.temp_c,w.wind_ms,w.visibility_m
from (select * from int_airport_hours where cutoff>=timestamp '2023-01-01'
and cutoff<timestamp '2023-02-01') c
left join stg_weather w on c.airport=w.airport and w.available_at<=c.cutoff
qualify row_number() over(partition by c.airport,c.cutoff order by w.available_at desc nulls last)=1
order by c.airport,c.cutoff;
