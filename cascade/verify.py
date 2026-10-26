"""Audit frozen evidence, quickstart bytes and (when present) the full warehouse."""
from datetime import datetime
import hashlib,json
from pathlib import Path
import duckdb
from .ingest import ROOT,sha

def run():
    checks=[]
    def check(name,value,detail=None):
        checks.append({'check':name,'passed':bool(value),'detail':detail})
        if not value:raise AssertionError(f'{name}: {detail}')
    sample=json.loads((ROOT/'data/quickstart/manifest.json').read_text())
    check('quickstart_has_real_nonempty_partitions',len(sample['sources'])==16 and sample['total_bytes']>0)
    for s in sample['sources']:
        check('quickstart_hash:'+s['path'],sha(ROOT/s['path'])==s['sha256'])
    model=json.loads((ROOT/'reports/model_evaluation.json').read_text());sim=json.loads((ROOT/'reports/scenarios.json').read_text());replay=json.loads((ROOT/'web/dist/data/replay.json').read_text());eda=json.loads((ROOT/'reports/eda.json').read_text());bench=json.loads((ROOT/'reports/query_benchmark.json').read_text())
    check('five_models_three_chronological_folds',len(model['folds'])==3 and all(len(f['models'])==5 for f in model['folds']))
    for fold in model['folds']:
        check('mature_training_labels:'+fold['fold'],datetime.fromisoformat(fold['max_training_label_available_at'])<datetime.fromisoformat(fold['fit_before']))
        for name,m in fold['models'].items():
            check('calibration_complete:'+fold['fold']+':'+name,sum(b['n'] for b in m['calibration_bins'])==m['n'])
    check('source_snapshot_links',replay['meta']['source_snapshot']==sha(ROOT/'data/source_manifest.json'))
    check('model_code_fingerprint',model['implementation_sha256']==sha(ROOT/'cascade/modeling.py'))
    check('scenario_code_fingerprint',sim['implementation_sha256']==sha(ROOT/'cascade/simulation.py'))
    check('consistent_model_identity',model['run_id']==sim['model_run_id']==replay['meta']['model_run'])
    check('heldout_replay_days',sim['baseline_replay']['heldout_days']==92)
    check('physical_and_resource_invariants',all(sim['invariants'][x]==0 for x in ['budget_exceeded','negative_simulated_departure_delay','resource_increases_delay','aircraft_readiness_violations']) and sim['invariants']['aircraft_readiness_checks']>0)
    for d in sim['days']:
        for name,p in d['policies'].items():
            check('bounded_allocation:'+d['date']+':'+name,sum(p['allocation'].values())<=sim['budget'] and all(isinstance(v,int) and 0<=v<=2 for v in p['allocation'].values()) and p['simulated_reduction_minutes']>=0)
        check('sensitivity_grid:'+d['date'],len(d['sensitivity'])==9)
    check('ordinary_and_stress_replays',len(replay['days'])>=4 and {'ordinary','stress'}<={d['kind'] for d in replay['days']})
    check('evidence_backed_findings',len(eda['findings'])>=3 and all(all(f.get(k) for k in ['question','denominator','finding','limitation','decision','sql_url']) for f in eda['findings']))
    check('benchmark_identical_results',bench['identical_results'] and len({v['result_sha256'] for v in bench['queries'].values()})==1)
    check('benchmark_has_runtime_memory_explain',all(len(v['seconds'])==3 and v['max_peak_buffer_memory_bytes']>0 for v in bench['queries'].values()) and all((ROOT/f'reports/query_{n}_explain.txt').exists() for n in bench['queries']))
    db=ROOT/'data/cascade.duckdb'
    database_checked=False
    if db.exists():
        database_checked=True;c=duckdb.connect(str(db),read_only=True)
        check('full_year_not_quickstart',c.execute('select count(*) from flights').fetchone()[0]==1438465)
        manifest=json.loads((ROOT/'data/source_manifest.json').read_text())
        check('scoped_source_count_reconciliation',sum(s['scoped_rows'] for s in manifest['sources'] if 'month' in s)==c.execute('select count(*) from raw_flights').fetchone()[0])
        for source in manifest['sources']:
            path=ROOT/(f"data/processed/flights/year=2023/month={source['month']:02d}/flights.parquet" if 'month' in source else f"data/processed/weather/year=2023/station={source['station']}/weather.parquet")
            check('full_partition_hash:'+str(path.relative_to(ROOT)),sha(path)==source['parquet_sha256'])
        check('no_future_weather_or_events',c.execute('select count(*) from features where weather_available_at>cutoff or max_event_available_at>cutoff').fetchone()[0]==0)
        check('no_inconsistent_rotation_endpoints',c.execute('select count(*) from rotations r join flights f on f.flight_id=r.from_flight_id or f.flight_id=r.to_flight_id where f.arrival_inconsistent or f.scheduled_arr_clock_inconsistent or f.actual_dep_clock_inconsistent').fetchone()[0]==0)
        check('prediction_keys_unique',c.execute('select count(*) from (select airport,cutoff,model,fold,count(*) as n from predictions group by all having n<>1)').fetchone()[0]==0)
        for d in replay['days']:
            for f in d['frames']:
                cutoff=datetime.fromisoformat(f['cutoff'].removesuffix('Z'))
                for a in f['airports']:
                    row=c.execute('select target_n,target_rate,backlog_n from features where airport=? and cutoff=?',[a['airport'],cutoff]).fetchone()
                    check('export_matches_feature:'+a['airport']+':'+f['cutoff'],row==(a['scheduled'],a['target_rate'],a['backlog']))
                    value=c.execute('select prediction from predictions where model=? and airport=? and cutoff=? and split=\'test\'',[model['selected_model'],a['airport'],cutoff]).fetchone()
                    check('export_matches_prediction:'+a['airport']+':'+f['cutoff'],(value[0] if value else None)==a['prediction'])
        c.close()
    report={'verified_at':datetime.now(__import__('datetime').timezone.utc).isoformat(),'passed':True,'checks':checks,'check_count':len(checks),'full_database_checked':database_checked,'limits':'This verifier covers file/data invariants. Public access, browser interaction and release provenance are independently verified in the release evidence; it does not infer them from file presence.'}
    (ROOT/'reports/verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return {'passed':True,'checks':len(checks),'full_database_checked':database_checked}
if __name__=='__main__':print(json.dumps(run(),indent=2))
