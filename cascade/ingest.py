"""Immutable, resumable public-source snapshots. Analysis stays in SQL."""
from __future__ import annotations
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
STATIONS = {'BWI':'72406093721','DAL':'72258013960','DEN':'72565003017','HOU':'72244012918','LAS':'72386023169','MDW':'72534014819','OAK':'72493023230','PHX':'72278023183'}
BTS = 'https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_{month}.zip'
COLUMNS = ['Year','Quarter','Month','DayofMonth','DayOfWeek','FlightDate','Reporting_Airline','DOT_ID_Reporting_Airline','Tail_Number','Flight_Number_Reporting_Airline','OriginAirportID','Origin','OriginCityName','DestAirportID','Dest','DestCityName','CRSDepTime','DepTime','DepDelay','CRSArrTime','ArrTime','ArrDelay','Cancelled','CancellationCode','Diverted','CRSElapsedTime','ActualElapsedTime','Distance','CarrierDelay','WeatherDelay','NASDelay','SecurityDelay','LateAircraftDelay']

def sha(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def download(url, target):
    """Restart incomplete transfer; only atomically promote complete non-HTML bodies."""
    target = Path(target)
    for attempt in range(3):
        part = target.with_suffix(target.suffix+'.part')
        try:
            with requests.get(url,stream=True,timeout=(30,180)) as r:
                r.raise_for_status()
                if 'text/html' in r.headers.get('Content-Type',''): raise ValueError(f'HTML, not source bytes: {url}')
                with part.open('wb') as f:
                    for b in r.iter_content(1024*1024): f.write(b)
                if r.headers.get('Content-Length') and part.stat().st_size != int(r.headers['Content-Length']): raise ValueError('Truncated transfer')
            os.replace(part,target)
            return
        except (requests.RequestException,ValueError):
            if attempt==2: raise
            time.sleep(2**attempt)

def sqlstr(v): return "'"+str(v).replace("'","''")+"'"

def atomic_json(path, value):
    path=Path(path);part=path.with_suffix(path.suffix+'.part')
    part.write_text(json.dumps(value,indent=2)+'\n');os.replace(part,path)

def cached_partition(out, marker):
    if not out.exists() or not marker.exists():return None
    try:
        m=json.loads(marker.read_text())
    except (json.JSONDecodeError,OSError):return None
    return m if sha(out)==m.get('parquet_sha256') else None

def promote_partition(part, out, marker):
    """Preserve prior bytes under their content hash before accepting a correction."""
    part,out,marker=Path(part),Path(out),Path(marker)
    if out.exists() and sha(out)!=sha(part):
        old_hash=sha(out)
        history=ROOT/'data/history'/out.parent.relative_to(ROOT/'data/processed')/old_hash
        history.mkdir(parents=True,exist_ok=True)
        backup=history/out.name
        if not backup.exists():shutil.copy2(out,backup)
        if sha(backup)!=old_hash:raise ValueError('Prior-partition backup failed verification')
        if marker.exists():shutil.copy2(marker,history/marker.name)
    os.replace(part,out)

def one_month(month, force=False):
    out = ROOT/f'data/processed/flights/year=2023/month={month:02d}/flights.parquet'
    marker = out.with_suffix('.manifest.json')
    if not force:
        existing=cached_partition(out,marker)
        if existing is not None:return existing
    out.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    url=BTS.format(month=month)
    # The official archive uses parentheses for December; discover exact name on failure.
    with tempfile.TemporaryDirectory(prefix='cascade-bts-',dir='/private/tmp' if Path('/private/tmp').exists() else None) as tmp:
        tmp=Path(tmp); archive=tmp/'source.zip'
        try: download(url,archive)
        except requests.HTTPError as e:
            if month!=12: raise
            url='https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2023_12.zip'
            download(url,archive)
        ziphash=sha(archive); zipbytes=archive.stat().st_size
        with zipfile.ZipFile(archive) as z:
            members=[n for n in z.namelist() if n.lower().endswith('.csv')]
            if len(members)!=1: raise ValueError(f'Expected one source CSV: {members}')
            csvpath=tmp/'source.csv'
            with z.open(members[0]) as a, csvpath.open('wb') as b: shutil.copyfileobj(a,b)
        con=duckdb.connect(); con.execute("set threads=2; set memory_limit='1GB'")
        con.execute(f"create view source as select * from read_csv({sqlstr(csvpath)},all_varchar=true,header=true)")
        columns=','.join('"'+c+'"' for c in COLUMNS)
        # Scan immutable CSV once into filtered table, preserve source clocks and flags.
        source_n=con.execute('select count(*) from source').fetchone()[0]
        con.execute(f"create table scoped as select {columns} from source where Reporting_Airline='WN'")
        metrics=con.execute("select count(*),sum(try_cast(Cancelled as double)),sum(try_cast(DepDelay as double)), count(*) filter(where DepDelay is null) from scoped").fetchone()
        part=out.with_suffix('.parquet.part')
        con.execute(f"copy scoped to {sqlstr(part)} (format parquet,compression zstd)")
        check=con.execute(f"select count(*),sum(try_cast(Cancelled as double)),sum(try_cast(DepDelay as double)), count(*) filter(where DepDelay is null) from read_parquet({sqlstr(part)})").fetchone()
        if metrics!=check: raise ValueError('Source/parquet reconciliation failed')
        promote_partition(part,out,marker)
        m={'source':'BTS Reporting Carrier On-Time Performance','url':url,'year':2023,'month':month,'scope':'WN, all domestic legs','archive_sha256':ziphash,'archive_bytes':zipbytes,'csv_sha256':sha(csvpath),'csv_bytes':csvpath.stat().st_size,'source_rows':source_n,'scoped_rows':metrics[0],'cancelled':metrics[1],'dep_delay_sum':metrics[2],'missing_dep_delay':metrics[3],'parquet_sha256':sha(out),'parquet_bytes':out.stat().st_size,'seconds':round(time.perf_counter()-started,3),'retrieved_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'reconciled':True}
        atomic_json(marker,m); con.close()
        print(f'BTS {month:02d}: {source_n:,} source -> {metrics[0]:,} WN rows ({m["seconds"]}s)',flush=True)
        return m

def one_weather(item,force=False):
    airport,station=item
    out=ROOT/f'data/processed/weather/year=2023/station={station}/weather.parquet'
    marker=out.with_suffix('.manifest.json')
    if not force:
        existing=cached_partition(out,marker)
        if existing is not None:return existing
    out.parent.mkdir(parents=True,exist_ok=True); started=time.perf_counter()
    url=f'https://noaa-global-hourly-pds.s3.amazonaws.com/2023/{station}.csv'
    with tempfile.TemporaryDirectory(prefix='cascade-noaa-') as tmp:
        path=Path(tmp)/'weather.csv';download(url,path)
        con=duckdb.connect();con.execute('set threads=2')
        con.execute(f'create table w as select * from read_csv({sqlstr(path)},all_varchar=true)')
        n=con.execute('select count(*) from w').fetchone()[0]
        part=out.with_suffix('.parquet.part');con.execute(f'copy w to {sqlstr(part)} (format parquet,compression zstd)');promote_partition(part,out,marker)
        m={'source':'NOAA ISD Global Hourly','url':url,'airport':airport,'station':station,'source_rows':n,'csv_sha256':sha(path),'csv_bytes':path.stat().st_size,'parquet_sha256':sha(out),'parquet_bytes':out.stat().st_size,'seconds':round(time.perf_counter()-started,3),'retrieved_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
        atomic_json(marker,m);con.close()
        print(f'NOAA {airport}: {n:,} observations ({m["seconds"]}s)',flush=True);return m

def run(months=range(1,13),force=False):
    start=time.perf_counter()
    jobs=[('bts',m) for m in months]+[('weather',a) for a in STATIONS.items()]
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(one_month,x,force) if k=='bts' else pool.submit(one_weather,x,force) for k,x in jobs]
        results=[f.result() for f in futures]
    manifest={'dataset':'CASCADE WN 2023 v1','sources':results,'ingest_wall_seconds':round(time.perf_counter()-start,3),'policy':'Immutable snapshots; rerun skips hash-verified partitions. --refresh atomically replaces a revised source partition. No unverified partial is promoted.'}
    atomic_json(ROOT/'data/source_manifest.json',manifest)
    return manifest
if __name__=='__main__':run()
