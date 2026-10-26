"""Execute production SQL on edge cases whose correct outcomes matter."""
from datetime import datetime
from pathlib import Path
import duckdb
import pytest
from cascade.ingest import COLUMNS
ROOT=Path(__file__).resolve().parents[1]

def run_sql(con,path,replacements):
    sql=(ROOT/path).read_text()
    for old,new in replacements.items():sql=sql.replace(old,new)
    return con.execute(sql)

def fixture_db():
    con=duckdb.connect();con.execute("set timezone='UTC'")
    con.execute('create table raw_flights('+','.join('"'+c+'" varchar' for c in COLUMNS)+')')
    con.execute('create table airports(airport varchar,timezone varchar,station varchar)')
    con.execute("insert into airports values ('DEN','America/Denver','72565003017'),('MDW','America/Chicago','72534014819')")
    return con

def add(con,number='1',**kwargs):
    row=dict(Year='2023',Quarter='1',Month='1',DayofMonth='1',DayOfWeek='7',FlightDate='2023-01-01',Reporting_Airline='WN',Flight_Number_Reporting_Airline=number,Tail_Number='N1',Origin='DEN',Dest='MDW',CRSDepTime='2350',DepTime='2345',DepDelay='-5',CRSArrTime='0200',ArrTime='0155',ArrDelay='-5',Cancelled='0',Diverted='0',CRSElapsedTime='70',ActualElapsedTime='70',Distance='900')
    row.update(kwargs)
    con.execute('insert into raw_flights values ('+','.join('?' for _ in COLUMNS)+')',[row.get(k) for k in COLUMNS])

def materialize(con):
    run_sql(con,'dbt/models/staging/stg_flights.sql',{"{{ source('public_snapshot','raw_flights') }}":'raw_flights'})
    con.execute('create table stg_flights as '+con.sql('select 1').query) if False else None
    sql=(ROOT/'dbt/models/staging/stg_flights.sql').read_text().replace("{{ source('public_snapshot','raw_flights') }}",'raw_flights')
    con.execute('create table stg_flights as '+sql)
    sql=(ROOT/'dbt/models/intermediate/int_flight_times.sql').read_text().replace("{{ ref('stg_flights') }}",'stg_flights').replace("{{ ref('airports') }}",'airports')
    con.execute('create table int_flight_times as '+sql)
    sql=(ROOT/'dbt/models/marts/flights.sql').read_text().replace("{{ ref('int_flight_times') }}",'int_flight_times')
    con.execute('create table flights as '+sql)


def test_rollover_and_signed_early_departure():
    c=fixture_db();add(c);materialize(c)
    r=c.execute('select sched_dep,sched_arr,actual_dep,actual_arr,dep_delay,arrival_inconsistent from flights').fetchone()
    assert r==(datetime(2023,1,2,6,50),datetime(2023,1,2,8),datetime(2023,1,2,6,45),datetime(2023,1,2,7,55),-5.,False)


def test_2400_and_missing_outcomes():
    c=fixture_db();add(c,CRSDepTime='2400',DepDelay=None,ArrDelay=None,ActualElapsedTime=None,DepTime=None,ArrTime=None);materialize(c)
    assert c.execute('select sched_dep,actual_dep,actual_arr,arr_delay from flights').fetchone()==(datetime(2023,1,2,7),None,None,None)

@pytest.mark.parametrize('day,clock,reason',[('2023-03-12','0230','dst_gap'),('2023-11-05','0130','dst_fold')])
def test_dst_times_quarantined(day,clock,reason):
    c=fixture_db();add(c,FlightDate=day,CRSDepTime=clock);materialize(c)
    assert c.execute('select time_quality from int_flight_times').fetchone()[0]==reason
    assert c.execute('select count(*) from flights').fetchone()[0]==0


def test_cancelled_diverted_and_unknown_are_not_filled():
    c=fixture_db();add(c,number='1',Cancelled='1',Tail_Number=None,DepDelay=None,ArrDelay=None,ActualElapsedTime=None)
    add(c,number='2',Diverted='1',ArrDelay=None)
    add(c,number='3',DepDelay=None,ArrDelay=None,ActualElapsedTime=None)
    materialize(c)
    assert c.execute("select actual_dep,actual_arr,tail from flights where flight_number='1'").fetchone()==(None,None,None)
    assert c.execute("select actual_arr from flights where flight_number='2'").fetchone()[0] is None
    assert c.execute("select dep_delay,arr_delay from flights where flight_number='3'").fetchone()==(None,None)


def test_exact_duplicates_accounted_conflicting_corrections_quarantined():
    c=fixture_db();add(c);add(c);add(c,number='2');add(c,number='2',DepDelay='65')
    materialize(c)
    assert c.execute("select duplicate_n,revision_n from stg_flights where flight_number='1'").fetchone()==(2,1)
    assert c.execute("select revision_n from stg_flights where flight_number='2'").fetchone()[0]==2
    assert c.execute('select count(*) from flights').fetchone()[0]==1


def test_weather_quality_priority_and_asof_no_fanout():
    c=fixture_db();c.execute('create table raw_weather(STATION varchar, DATE varchar, SOURCE varchar, REPORT_TYPE varchar,TMP varchar,WND varchar,VIS varchar)')
    c.executemany('insert into raw_weather values (?,?,?,?,?,?,?)',[
        ('72565003017','2023-01-01T00:00:00','4','FM-12','+0100,1','090,1,N,0040,1','016000,1,N,1'),
        ('72565003017','2023-01-01T00:00:00','4','FM-15','+0120,1','090,1,N,0050,1','016000,1,N,1'),
        ('72565003017','2023-01-01T02:00:00','4','FM-15','+9999,9','999,9,9,9999,9','999999,9,9,9')])
    sql=(ROOT/'dbt/models/staging/stg_weather.sql').read_text().replace("{{ source('public_snapshot','raw_weather') }}",'raw_weather').replace("{{ ref('airports') }}",'airports')
    c.execute('create table stg_weather as '+sql)
    assert c.execute('select temp_c,wind_ms from stg_weather order by observed_at').fetchall()==[(12.,5.),(None,None)]
    assert c.execute("select count(*),max(temp_c) from (select timestamp '2023-01-01 00:30' as cutoff,'DEN' as airport) g asof left join stg_weather w on g.airport=w.airport and g.cutoff>=w.available_at").fetchone()==(1,None)
    assert c.execute("select temp_c from (select timestamp '2023-01-01 01:30' as cutoff,'DEN' as airport) g asof left join stg_weather w on g.airport=w.airport and g.cutoff>=w.available_at").fetchone()[0]==12.


def test_backlog_counts_exact_publication_boundary():
    c=duckdb.connect();c.execute("set timezone='UTC'")
    c.execute("create table airports as select 'DEN' as airport,'America/Denver' as timezone,true as focal")
    c.execute("create table flights as select 'DEN' as origin,timestamp '2023-01-01 12:45' as sched_dep, null::timestamp as actual_dep,null::double as dep_delay,false as cancelled")
    c.execute("create table int_airport_hours as select 'DEN' as airport,unnest([timestamp '2023-01-01 13:00',timestamp '2023-01-01 14:00']) as cutoff")
    c.execute("create table int_hourly_events(airport varchar,event_hour timestamp,observed_n integer,observed_late_n integer,max_available_at timestamp)")
    sql=(ROOT/'dbt/models/intermediate/int_cutoff_features.sql').read_text()
    for table in ['airports','flights','int_airport_hours','int_hourly_events']:sql=sql.replace("{{ ref('"+table+"') }}",table)
    assert c.execute('select cutoff,backlog_n from ('+sql+') order by cutoff').fetchall()==[(datetime(2023,1,1,13),1),(datetime(2023,1,1,14),1)]
