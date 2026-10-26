"""Small source-reconciled January reporting-carrier benchmark for selection bias."""
from pathlib import Path
import json,tempfile,time,zipfile,shutil
import duckdb
from .ingest import ROOT,BTS,STATIONS,download,sha,sqlstr,atomic_json

def write_from_connection(con,source_info):
    out=ROOT/'data/benchmarks/carrier_cohorts_2023_01.parquet';out.parent.mkdir(parents=True,exist_ok=True)
    airports=','.join(sqlstr(x) for x in STATIONS)
    query=f"""select Reporting_Airline as carrier,Origin as airport,'2023-01' as period,
      count(*) as scheduled_n,
      count(*) filter(where try_cast(Cancelled as double)=1 or try_cast(DepDelay as double)>=15) as disrupted_n,
      count(*) filter(where try_cast(Cancelled as double)=1) as cancelled_n,
      count(*) filter(where try_cast(Cancelled as double)=0 and try_cast(DepDelay as double) is null) as unknown_n,
      count(try_cast(DepDelay as double)) as observed_gate_delay_n,
      avg(try_cast(DepDelay as double)) as mean_dep_delay,
      quantile_cont(try_cast(DepDelay as double),.99) as p99_dep_delay
      from source where Origin in ({airports}) group by 1,2,3 order by 1,2"""
    part=out.with_suffix('.part');con.execute(f'copy ({query}) to {sqlstr(part)} (format parquet,compression zstd)')
    import os
    os.replace(part,out)
    focal_source_n=con.execute(f'select count(*) from source where Origin in ({airports})').fetchone()[0]
    if con.execute(f'select sum(scheduled_n) from read_parquet({sqlstr(out)})').fetchone()[0]!=focal_source_n:raise ValueError('Carrier cohort count reconciliation failed')
    info={'source':'BTS January2023Reporting Carrier, all reporting airlines at8focal origins','url':BTS.format(month=1),'archive_sha256':source_info['archive_sha256'],'source_rows':source_info['source_rows'],'focal_source_rows':focal_source_n,'parquet_sha256':sha(out),'parquet_bytes':out.stat().st_size,'query':query,'limitation':'A January selection-bias benchmark, not a full-year or causal ranking. Reporting carriers have different airport, route and schedule mixes; small cohorts remain visible.'}
    atomic_json(ROOT/'data/benchmarks/carrier_cohorts_manifest.json',info);return info

def run():
    source_info=json.loads((ROOT/'data/processed/flights/year=2023/month=01/flights.manifest.json').read_text())
    with tempfile.TemporaryDirectory(prefix='cascade-carrier-benchmark-') as tmp:
        tmp=Path(tmp);archive=tmp/'source.zip';download(BTS.format(month=1),archive)
        if sha(archive)!=source_info['archive_sha256']:raise ValueError('January source revision differs from frozen warehouse; reconcile snapshots before comparing')
        with zipfile.ZipFile(archive) as z:
            member=next(n for n in z.namelist() if n.lower().endswith('.csv'));csv=tmp/'source.csv'
            with z.open(member) as a,csv.open('wb') as b:shutil.copyfileobj(a,b)
        con=duckdb.connect();con.execute('set threads=2')
        con.execute(f'create view source as select * from read_csv({sqlstr(csv)},all_varchar=true)')
        if con.execute('select count(*) from source').fetchone()[0]!=source_info['source_rows']:raise ValueError('January source count changed')
        result=write_from_connection(con,source_info);con.close();print(json.dumps(result,indent=2));return result
if __name__=='__main__':run()
