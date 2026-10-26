"""Identical-result EXPLAIN/profile comparison: rank-all-weather vs ASOF."""
import hashlib,json,statistics,time
from pathlib import Path
import duckdb
from .ingest import ROOT,sqlstr

BASE="""select c.airport,c.cutoff,w.observed_at,w.temp_c,w.wind_ms,w.visibility_m
from (select * from int_airport_hours where cutoff>=timestamp '2023-01-01'
and cutoff<timestamp '2023-02-01') c
left join stg_weather w on c.airport=w.airport and w.available_at<=c.cutoff
qualify row_number() over(partition by c.airport,c.cutoff order by w.available_at desc nulls last)=1
order by c.airport,c.cutoff"""
FAST="""select c.airport,c.cutoff,w.observed_at,w.temp_c,w.wind_ms,w.visibility_m
from (select * from int_airport_hours where cutoff>=timestamp '2023-01-01'
and cutoff<timestamp '2023-02-01') c
asof left join stg_weather w on c.airport=w.airport and c.cutoff>=w.available_at
order by c.airport,c.cutoff"""

def run(db_path=None,output_dir=None):
    db=Path(db_path or ROOT/'data/cascade.duckdb');out=Path(output_dir or ROOT/'reports');out.mkdir(exist_ok=True,parents=True)
    reports={}; digests={}
    for name,query in [('range_join_rank',BASE),('asof',FAST)]:
        times=[];peaks=[];result=None
        for i in range(3):
            con=duckdb.connect(str(db),read_only=True)
            con.execute("set threads=2;set memory_limit='1GB'")
            if i==0:
                plan=con.execute('explain '+query).fetchall()
                (out/f'query_{name}_explain.txt').write_text('\n'.join(str(x[1]) for x in plan))
            profile=out/f'query_{name}_profile_{i}.json'
            con.execute("pragma enable_profiling='json'")
            con.execute('set profiling_output='+sqlstr(profile))
            t=time.perf_counter();result=con.execute(query).fetchall();times.append(time.perf_counter()-t)
            con.close();p=json.loads(profile.read_text());peaks.append(p.get('system_peak_buffer_memory'))
        digests[name]=hashlib.sha256(json.dumps(result,default=str,allow_nan=False).encode()).hexdigest()
        reports[name]={'rows':len(result),'seconds':times,'median_seconds':statistics.median(times),'peak_buffer_memory_bytes':peaks,'max_peak_buffer_memory_bytes':max(peaks),'result_sha256':digests[name],'query':query}
    if len(set(digests.values()))!=1:raise AssertionError('Optimized query changed results')
    report={'comparison':'January 2023: eight airports × hourly cutoffs; latest available NOAA observation',
        'duckdb_version':duckdb.__version__,'threads':2,'memory_limit':'1GB','repetitions':3,'fresh_connection_each_run':True,
        'identical_results':True,'queries':reports,
        'speedup':reports['range_join_rank']['median_seconds']/reports['asof']['median_seconds'],
        'buffer_memory_reduction':1-reports['asof']['max_peak_buffer_memory_bytes']/reports['range_join_rank']['max_peak_buffer_memory_bytes'],
        'limitations':'Measured local execution, including result materialization; OS file cache not cleared. Buffer memory is DuckDB profiler peak, not total Python/process RSS. January subset; not a full-warehouse benchmark.'}
    (out/'query_benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'sql/benchmark_before.sql').write_text(BASE+';\n');(ROOT/'sql/benchmark_after.sql').write_text(FAST+';\n')
    return report
if __name__=='__main__':print(json.dumps(run(),indent=2))
