"""Build source views and the substantive dbt SQL DAG."""
from pathlib import Path
import csv,json,os,subprocess,time,sys
import airportsdata
import duckdb
from .ingest import ROOT,STATIONS,sqlstr

def run(quickstart=False, db_path=None):
    started=time.perf_counter(); os.chdir(ROOT)
    data=ROOT/('data/quickstart' if quickstart else 'data/processed')
    flights=sorted(data.glob('flights/**/*.parquet'));weather=sorted(data.glob('weather/**/*.parquet'))
    if not flights or not weather: raise FileNotFoundError('Run ingest or provide bundled quickstart partitions first')
    db=Path(db_path) if db_path else ROOT/('data/quickstart.duckdb' if quickstart else 'data/cascade.duckdb'); con=duckdb.connect(str(db));con.execute("set timezone='UTC'")
    con.execute(f"create or replace view raw_flights as select * from read_parquet({sqlstr(data/'flights/**/*.parquet')},hive_partitioning=false)")
    con.execute(f"create or replace view raw_weather as select * from read_parquet({sqlstr(data/'weather/**/*.parquet')},union_by_name=true,hive_partitioning=false)")
    codes=[r[0] for r in con.execute('select Origin from raw_flights union select Dest from raw_flights order by 1').fetchall()]
    all_airports=airportsdata.load('IATA')
    missing=[c for c in codes if c not in all_airports]
    if missing:raise ValueError(f'Missing timezone mapping: {missing}')
    if not quickstart or not (ROOT/'dbt/seeds/airports.csv').exists():
        with (ROOT/'dbt/seeds/airports.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['airport','name','lat','lon','timezone','station','focal'])
            for code in codes:
                a=all_airports[code];w.writerow([code,a['name'],a['lat'],a['lon'],a['tz'],STATIONS.get(code,''),str(code in STATIONS).lower()])
    con.close()
    env={**os.environ,'CASCADE_DB':str(db)}
    subprocess.run([str(Path(sys.executable).parent/'dbt'),'build','--project-dir','dbt','--profiles-dir','dbt'],check=True,env=env)
    con=duckdb.connect(str(db),read_only=True)
    counts={t:con.execute(f'select count(*) from {t}').fetchone()[0] for t in ['raw_flights','stg_flights','flights','raw_weather','stg_weather','rotations','features']}
    run={'mode':'quickstart' if quickstart else 'full','seconds':round(time.perf_counter()-started,3),'counts':counts,'duckdb_version':duckdb.__version__,'db_bytes':db.stat().st_size,'source_files':len(flights)+len(weather)}
    (ROOT/('reports/quickstart_warehouse_run.json' if quickstart else 'reports/warehouse_run.json')).write_text(json.dumps(run,indent=2)+'\n');con.close();return run
