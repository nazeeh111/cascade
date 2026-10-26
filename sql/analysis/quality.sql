-- Q: Which records or edges are unsuitable, and where does missingness concentrate?
select 'flight_time' as kind,time_quality as reason,count(*) as n from int_flight_times group by 1,2
union all select 'rotation',rotation_quality,count(*) from int_rotations group by 1,2
union all select 'weather_report',report_type,count(*) from stg_weather group by 1,2
