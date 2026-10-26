select station,observed_at from {{ ref('stg_weather') }} group by 1,2 having count(*)<>1
union all
select station,observed_at from {{ ref('stg_weather') }}
where available_at<observed_at or wind_ms<0 or visibility_m<0 or temp_c not between -93 and 61
