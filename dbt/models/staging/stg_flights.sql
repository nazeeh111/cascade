-- Grain: one deterministic BTS reporting-carrier scheduled flight key.
-- Exact duplicate rows collapse. Conflicting revisions are exposed and block release.
with casted as (
 select md5(concat_ws('|',FlightDate, Reporting_Airline,
      Flight_Number_Reporting_Airline, Origin, Dest, CRSDepTime)) as flight_id,
   try_cast(FlightDate as date) as flight_date, Reporting_Airline as carrier,
   Flight_Number_Reporting_Airline as flight_number, nullif(Tail_Number,'') as tail,
   Origin as origin, Dest as dest, try_cast(CRSDepTime as integer) as dep_clock,
   try_cast(CRSArrTime as integer) as arr_clock,
   try_cast(DepTime as integer) as actual_dep_clock,
   try_cast(ArrTime as integer) as actual_arr_clock,
   try_cast(DepDelay as double) as dep_delay,
   try_cast(ArrDelay as double) as arr_delay,
   try_cast(CRSElapsedTime as double) as scheduled_elapsed_min,
   try_cast(ActualElapsedTime as double) as actual_elapsed_min,
   try_cast(Cancelled as double)=1 as cancelled,
   try_cast(Diverted as double)=1 as diverted,
   CancellationCode as cancellation_code,
   try_cast(Distance as double) as distance,
   try_cast(CarrierDelay as double) as carrier_delay,
   try_cast(WeatherDelay as double) as weather_delay,
   try_cast(NASDelay as double) as nas_delay,
   try_cast(SecurityDelay as double) as security_delay,
   try_cast(LateAircraftDelay as double) as late_aircraft_delay,
   printf('2023-%02d',try_cast(Month as integer)) as source_month,
   md5(to_json(struct_pack(FlightDate,Reporting_Airline,Flight_Number_Reporting_Airline,
      Tail_Number,Origin,Dest,CRSDepTime,DepTime,DepDelay,CRSArrTime,ArrTime,ArrDelay,
      Cancelled,Diverted,CRSElapsedTime,ActualElapsedTime,Distance,
      CancellationCode,CarrierDelay,WeatherDelay,NASDelay,SecurityDelay,LateAircraftDelay))) as row_hash
 from {{ source('public_snapshot','raw_flights') }}
), dedup as (
 select *, count(*) over(partition by flight_id) as duplicate_n,
   count(distinct row_hash) over(partition by flight_id) as revision_n
 from casted
 qualify row_number() over(partition by flight_id order by row_hash)=1
)
select * from dedup
