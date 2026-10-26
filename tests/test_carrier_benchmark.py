import duckdb
from cascade import carrier_benchmark as benchmark

def test_carrier_cohort_preserves_cancellation_censoring_signed_delay_and_grain(tmp_path,monkeypatch):
    monkeypatch.setattr(benchmark,'ROOT',tmp_path)
    c=duckdb.connect();c.execute('create table source(Reporting_Airline varchar,Origin varchar,Cancelled varchar,DepDelay varchar)')
    c.execute("insert into source values ('WN','DEN','0','-5'),('WN','DEN','1',null),('AA','DEN','0','30'),('AA','DEN','0',null),('WN','AAA','0','0')")
    result=benchmark.write_from_connection(c,{'archive_sha256':'fixture','source_rows':5})
    assert result['focal_source_rows']==4
    rows=c.execute("select carrier,scheduled_n,disrupted_n,cancelled_n,unknown_n,mean_dep_delay from read_parquet(?) order by carrier",[str(tmp_path/'data/benchmarks/carrier_cohorts_2023_01.parquet')]).fetchall()
    assert rows==[('AA',2,1,0,1,30.),('WN',2,1,1,0,-5.)]
