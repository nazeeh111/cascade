-- Grain station + UTC observation timestamp. Keep deterministic report priority.
with parsed as (
 select STATION as station, try_cast(DATE as timestamp) as observed_at,
    SOURCE as observation_source, trim(REPORT_TYPE) as report_type,
    try_cast(split_part(TMP,',',1) as double)/10 as t,
    split_part(TMP,',',2) as tq,
    try_cast(split_part(WND,',',4) as double)/10 as w,
    split_part(WND,',',5) as wq,
    try_cast(split_part(VIS,',',1) as double) as v,
    split_part(VIS,',',2) as vq,
    md5(to_json(struct_pack(STATION,DATE,SOURCE,REPORT_TYPE,TMP,WND,VIS))) as observation_hash
 from {{ source('public_snapshot','raw_weather') }}
 where coalesce(trim(REPORT_TYPE),'') not in ('SOD','SOM')
), cleaned as (
 select *, case when tq in ('0','1','4','5') and t between -93 and 61 then t end as temp_c,
   case when wq in ('0','1','4','5') and w between 0 and 90 then w end as wind_ms,
   case when vq in ('0','1','4','5') and v between 0 and 160000 then v end as visibility_m
 from parsed where observed_at is not null
)
select a.airport,c.station,c.observed_at,c.observed_at+interval '60 minutes' as available_at,
   temp_c,wind_ms,visibility_m,report_type,observation_source,observation_hash,
   count(*) over(partition by c.station,observed_at) as duplicate_n
from cleaned c join {{ ref('airports') }} a on c.station=a.station
qualify row_number() over(partition by c.station,observed_at order by
  case report_type when 'FM-15' then 0 when 'FM-16' then 1 when 'FM-12' then 2 else 3 end,
  (temp_c is null)::integer+(wind_ms is null)::integer+(visibility_m is null)::integer,observation_hash)=1
