"""Small, attributed real-data extract, not synthetic and not a full-year benchmark."""
from pathlib import Path
import json,os
import duckdb
from .ingest import ROOT,sha,sqlstr

WINDOWS="((month=1 and day<=7) or (month in (6,7,8,9,10,11,12) and day<=3))"

def package():
    con=duckdb.connect(str(ROOT/'data/cascade.duckdb'),read_only=True)
    root=ROOT/'data/quickstart';sources=[]
    for month in (1,6,7,8,9,10,11,12):
        days=7 if month==1 else 3
        out=root/f'flights/year=2023/month={month:02d}/flights.parquet';out.parent.mkdir(parents=True,exist_ok=True)
        query=f"select * from raw_flights where try_cast(Month as integer)={month} and try_cast(DayofMonth as integer)<={days}"
        part=out.with_suffix('.part');con.execute(f'copy ({query}) to {sqlstr(part)} (format parquet,compression zstd)');os.replace(part,out)
        sources.append({'path':str(out.relative_to(ROOT)),'rows':con.execute(f'select count(*) from ({query})').fetchone()[0],'sha256':sha(out),'bytes':out.stat().st_size})
    stations=con.execute('select airport,station from airports where focal order by airport').fetchall()
    for airport,station in stations:
        out=root/f'weather/year=2023/station={station}/weather.parquet';out.parent.mkdir(parents=True,exist_ok=True)
        # Retain one prior UTC day to support as-of startup in each selected period.
        query=f"select * from raw_weather where STATION={sqlstr(station)} and ((month(try_cast(DATE as timestamp))=1 and day(try_cast(DATE as timestamp))<=8) or (month(try_cast(DATE as timestamp)) in (6,7,8,9,10,11,12) and day(try_cast(DATE as timestamp))<=4))"
        part=out.with_suffix('.part');con.execute(f'copy ({query}) to {sqlstr(part)} (format parquet,compression zstd)');os.replace(part,out)
        sources.append({'path':str(out.relative_to(ROOT)),'airport':airport,'rows':con.execute(f'select count(*) from ({query})').fetchone()[0],'sha256':sha(out),'bytes':out.stat().st_size})
    report={'name':'CASCADE small real-data quickstart','selection':'WN departures dated Jan1–7 and Jun/Jul/Aug/Sep/Oct/Nov/Dec1–3,2023; eight NOAA stations same periods plus one trailing UTC day. Dates are discontinuous.','sources':sources,'total_bytes':sum(s['bytes'] for s in sources),'source_manifest_sha256':sha(ROOT/'data/source_manifest.json'),'license':'US federal BTS/NOAA source data: public-domain US government records; see DATA_LICENSE.md. Selection and code MIT. airportsdata metadata MIT. No airline endorsement.','limitation':'A functional warehouse quickstart, not sufficient for the published full-year scientific results. Do not infer annual rates from these selected dates. Frozen public replay derives from the separately measured full run.'}
    (root/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');con.close();return report
if __name__=='__main__':print(json.dumps(package(),indent=2))
