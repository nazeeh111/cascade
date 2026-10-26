"""Export only computed, source-linked held-out replay evidence."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,shutil,ast
import duckdb
from .ingest import ROOT,sha,atomic_text
from .eda import records

REPO='https://github.com/nazeeh111/cascade'
BASE=REPO+'/blob/v0.1.0/'

def run():
    con=duckdb.connect(str(ROOT/'data/cascade.duckdb'),read_only=True)
    model=json.loads((ROOT/'reports/model_evaluation.json').read_text());sim=json.loads((ROOT/'reports/scenarios.json').read_text());eda=json.loads((ROOT/'reports/eda.json').read_text())
    selected=model['selected_model'];snapshot=sha(ROOT/'data/source_manifest.json')
    literals=[n.value for n in ast.walk(ast.parse((ROOT/'cascade/simulation.py').read_text())) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('SELECT f.flight_id,f.origin,f.dest')]
    if len(literals)!=1:raise ValueError('Scenario provenance query is ambiguous')
    (ROOT/'sql/scenario_inputs.sql').write_text('-- Exact query executed by cascade/simulation.py; parameters cutoff−12h and cutoff+8h.\n-- Retrospective actual-tail topology, not a cutoff-safe forecast feature query.\n'+literals[0].strip()+';\n')
    cur=con.execute((ROOT/'sql/app_days.sql').read_text(),[selected]);daily=cur.fetchall()
    if len(daily)<4:raise ValueError('Full held-out replay requires ordinary and stress days')
    # Two central/ordinary days and two high-stress days; no cherry-picked forecast tuning.
    chosen=[(daily[len(daily)//3],'ordinary'),(daily[len(daily)//2],'ordinary'),(daily[-2],'stress'),(daily[-1],'stress')]
    chosen=sorted({r[0]:(r,k) for r,k in chosen}.values(),key=lambda x:(x[1]=='stress',x[0][0]))
    scenario_by_date={d['date']:d for d in sim['days']};days=[]
    for row,kind in chosen:
        d=row[0];start=datetime.combine(d,datetime.min.time());stop=start+timedelta(days=1)
        cur=con.execute((ROOT/'sql/app_replay.sql').read_text(),[selected,start,stop]);keys=[x[0] for x in cur.description]
        data=[dict(zip(keys,r)) for r in cur.fetchall()];frames=[]
        for cutoff in sorted({r['cutoff'] for r in data}):
            cur=con.execute((ROOT/'sql/app_edges.sql').read_text(),[cutoff,cutoff+timedelta(hours=2)]);edges=[{'origin':a,'dest':b,'flights':n} for a,b,n in cur.fetchall()]
            airports=[]
            for r in data:
                if r['cutoff']!=cutoff:continue
                airports.append({'airport':r['airport'],'scheduled':r['scheduled'],'observed_rate':r['observed_rate'],'prediction':r['prediction'],'target_rate':r['target_rate'],'backlog':r['backlog'],
                  'weather':{'temp_c':r['temp_c'],'wind_ms':r['wind_ms'],'visibility_m':r['visibility_m'],'age_min':r['weather_age_min']},
                  'weather_available_at':r['weather_available_at'],'max_event_available_at':r['max_event_available_at'],'label_available_at':r['label_available_at']})
            frames.append({'cutoff':cutoff.isoformat()+'Z','airports':airports,'edges':edges})
        sd=scenario_by_date.get(str(d));scenarios=[]
        if sd:
            baseline=sd['policies']['none']['simulated_departure_delay_minutes']
            for policy,p in sd['policies'].items():
                scenarios.append({'budget':sim['budget'],'policy':policy,'baseline_delay_min':baseline,'scenario_delay_min':p['simulated_departure_delay_minutes'],'benefit_min':p['simulated_reduction_minutes'],'allocations':p['allocation'],'cutoff':sd['cutoff']+'Z',
                  'resource_description':f"{sim['budget']} hypothetical teams; at most 2 per airport. Each serves up to 2 scheduled legs and removes at most 15 minutes from the external delay floor; aircraft readiness remains binding.",
                  'note':f"Fixed 16:00 UTC scenario, independent of the replay cursor. Denominator: all WN domestic completed legs scheduled in the following 8h; resources are restricted to eight focal airports. Baseline replay MAE on this day: {sd['replay']['mae_minutes']:.1f} min across {sd['replay']['n_completed_flights']:,} completed flights. Full held-out replay late15 recall: {100*sim['baseline_replay']['delay15_recall']:.1f}%; tail events are poorly represented. Actual-tail topology uses hindsight; no cancellation recovery, causal savings or airline staffing claim.",
                  'model_run':model['run_id'],'scenario_run':sim['run_id']})
        days.append({'date':str(d),'label':'HIGH DISRUPTION' if kind=='stress' else 'ORDINARY DAY','kind':kind,'selection_rate':row[1],'frames':frames,'scenarios':scenarios})
    airport_rows=records(con,'select airport,name,lat,lon,timezone from airports where focal order by airport')
    heldout=next(f for f in model['folds'] if f['split']=='test')
    metrics=[{'model':n,'split':'Oct–Dec 2023','mae':m['mae'],'rmse':m['rmse'],'severe_recall':m['severe_recall'],'calibration_mae':m['calibration_mae'],'runtime_seconds':m['fit_predict_seconds']} for n,m in heldout['models'].items()]
    delta=model['graph_contribution']['heldout_mae_reduction']
    summary=f"Frozen October–December holdout; 2h departure-disruption rate. {selected.replace('_',' ')} was selected using August/September validation. Graph versus temporal residual MAE reduction: {delta*100:+.3f} percentage points. This small/descriptive comparison is not a broad superiority claim. Calibration and 7-day block-bootstrap uncertainty are in the model report."
    findings=[{**f,'sql_url':BASE+f['sql_url']} for f in eda['findings']]
    data={'meta':{'repository_url':REPO,'source_snapshot':snapshot,'model_run':model['run_id'],'forecast_model':selected,'sql_url':BASE+'sql/app_replay.sql','edge_sql_url':BASE+'sql/app_edges.sql','scenario_sql_url':BASE+'sql/scenario_inputs.sql','source_url':BASE+'data/source_manifest.json','model_url':BASE+'reports/model_evaluation.json','scenario_url':BASE+'reports/scenarios.json','analysis_url':BASE+'reports/EDA.md','generated_at':datetime.now(timezone.utc).isoformat(),'flight_count':con.execute('select count(*) from flights').fetchone()[0],'weather_count':con.execute('select count(*) from raw_weather').fetchone()[0],
      'day_selection':'Two ordinary quantile days and two highest actual-rate days, selected retrospectively for contrasting replay; overlapping2h labels weight schedule counts. No model tuning uses this selection.','edge_definition':'Focal scheduled directed departures in next 2h; visualization aggregates both directions.'},'airports':airport_rows,'days':days,'models':{'summary':summary,'metrics':metrics},'findings':findings,
      'provenance':[{'label':'Source snapshots', 'url':BASE+'data/source_manifest.json'},{'label':'Carrier benchmark snapshot','url':BASE+'data/benchmarks/carrier_cohorts_manifest.json'},{'label':'Generating replay SQL','url':BASE+'sql/app_replay.sql'},{'label':'Model run & calibration','url':BASE+'reports/model_evaluation.json'},{'label':'Scenario input SQL','url':BASE+'sql/scenario_inputs.sql'},{'label':'Simulation & sensitivity','url':BASE+'reports/scenarios.json'},{'label':'SQL findings & cohorts','url':BASE+'reports/EDA.md'},{'label':'Small real-data quickstart','url':REPO+'#reproduce'},{'label':'Source dictionaries & rights','url':BASE+'docs/SOURCES.md'}]}
    out=ROOT/'web/dist/data';out.mkdir(parents=True,exist_ok=True)
    atomic_text(out/'replay.json',json.dumps(data,default=str,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    con.close()
    # Human-readable evidence is available even when browsing the deployed static app alone.
    (ROOT/'web/dist/evidence').mkdir(exist_ok=True)
    for name in ['eda.html','model_evaluation.json','scenarios.json','query_benchmark.json']:
        shutil.copy2(ROOT/'reports'/name,ROOT/'web/dist/evidence'/name)
    return {'days':[d['date'] for d in days],'replay_bytes':(out/'replay.json').stat().st_size,'source_snapshot':snapshot,'model_run':model['run_id']}
if __name__=='__main__':print(json.dumps(run(),indent=2))
