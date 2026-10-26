"""Rerunnable SQL investigation and evidence-backed analytical findings."""
from pathlib import Path
import json,html
import duckdb
from .ingest import ROOT

def records(con,sql):
    c=con.execute(sql); names=[d[0] for d in c.description]
    return [dict(zip(names,r)) for r in c.fetchall()]

def run(db_path=None,output_dir=None):
    con=duckdb.connect(str(db_path or ROOT/'data/cascade.duckdb'),read_only=True)
    out=Path(output_dir or ROOT/'reports');out.mkdir(parents=True,exist_ok=True)
    tables={p.stem:records(con,p.read_text()) for p in sorted((ROOT/'sql/analysis').glob('*.sql'))}
    a=tables['airport_cohorts']; hi,lo=a[0],a[-1]
    rate=lambda r:100*r['disrupted_n']/(r['n']-r.get('unknown_n',0))
    rot={r['cohort']:r for r in tables['rotation_associations']}
    overview=tables['overview'][0]
    findings=[
     {'title':'Disruption differs within the same carrier network','question':'Which focal airports had the highest and lowest 2023 disruption rates?',
      'denominator':f"{sum(r['n'] for r in a):,} WN departures from eight focal airports; denominator excludes unknown noncancelled departure status.",
      'finding':f"{hi['airport']} recorded {rate(hi):.1f}% late15-or-cancelled departures ({hi['n']:,} scheduled), versus {rate(lo):.1f}% at {lo['airport']} ({lo['n']:,}).",
      'limitation':'One carrier and reporting year; route mix, schedule and weather differ. This ranking does not measure airport management quality.',
      'decision':'Use airport-specific baselines and compare within cohorts before allocating hypothetical resources.','sql_url':'sql/analysis/airport_cohorts.sql'},
     {'title':'Aircraft continuity marks association, not cause','question':'Is a late inbound associated with a delayed next departure on validated aircraft chains?',
      'denominator':f"{sum(r['n'] for r in rot.values()):,} immediate, validated same-tail domestic pairs with observed inbound and outbound delays; cancelled/diverted/gapped chains excluded.",
      'finding':f"Next departures were late15 in {100*rot['inbound_late15']['outbound_late_rate']:.1f}% of pairs after a late15 inbound, versus {100*rot['inbound_under15']['outbound_late_rate']:.1f}% after an inbound under15 minutes late.",
      'limitation':'Retrospective actual tails, shared weather/airport conditions, selection on completed legs and missing international legs prevent a causal interpretation.',
      'decision':'Use validated chains to investigate plausible propagation and test simulator assumptions; keep final tails out of forecasts.','sql_url':'sql/analysis/rotation_associations.sql'},
     {'title':'Averages conceal long tails and missing outcomes','question':'How much information is lost by reducing delay to a mean or filling missing arrival delays with zero?',
      'denominator':f"{overview['n']:,} deduplicated WN scheduled flights with departure-time checks passed; percentiles use non-null departure delay only.",
      'finding':f"Departure delay median was {overview['median_dep_delay']:.0f} min, mean {overview['mean_dep_delay']:.1f} min, and 99th percentile {overview['p99_dep_delay']:.0f} min. {overview['early_departure_n']:,} departures were early; {overview['missing_arr_delay_n']:,} arrival delays were unobserved.",
      'limitation':'Cancelled and diverted flights censor arrival delay; extreme delays contribute heavily to the mean. No passenger-weighted effect is available.',
      'decision':'Preserve signed early departures, report tails and cancellations alongside delay, and leave missing arrival outcomes null.','sql_url':'sql/analysis/overview.sql'}]
    weather=tables['weather_associations'];known=[r for r in weather if r['weather_group']!='missing_or_stale']; high=next((r for r in known if r['weather_group']=='wind_at_least_8mps'),None);base=next((r for r in known if r['weather_group']=='other_observed'),None)
    if high and base:
      findings.append({'title':'Weather is useful context with confounding','question':'How does departure disruption differ under recorded higher-wind conditions?',
       'denominator':f"{high['n']:,} focal departures with latest available wind ≥8 m/s, versus {base['n']:,} other observed-weather departures; visibility <3km has a separate cohort.",
       'finding':f"Higher-wind cohort disruption was {rate(high):.1f}%, versus {rate(base):.1f}% in the other-observed cohort.",
       'limitation':'As-of hourly observations assume 60-minute latency; QC-filtered readings can be absent. Airport, season and traffic confound the association.',
       'decision':'Include observed weather as a forecast feature, then judge incremental performance on future dates rather than treating association as causal.','sql_url':'sql/analysis/weather_associations.sql'})
    carrier_counts={}
    for r in tables['carrier_cohorts']:carrier_counts[r['carrier']]=carrier_counts.get(r['carrier'],0)+r['scheduled_n']
    carrier_total=sum(carrier_counts.values());wn_n=carrier_counts.get('WN',0)
    findings.append({'title':'The carrier scope is a deliberate selection','question':'How much of the January reporting-carrier traffic at the focal airports does the WN study cover?',
      'denominator':f"{carrier_total:,} scheduled departures in the January2023BTS reporting-carrier extract at the eight focal origins, including cancellations.",
      'finding':f"WN accounts for {wn_n:,} of those departures ({100*wn_n/carrier_total:.1f}%). The remaining reporting carriers have different airport, route and schedule mixes.",
      'limitation':'January only; selected reporting carriers and origins, not all US operations or passenger market share. The comparison cannot isolate an airline effect.',
      'decision':'Interpret the forecast as WN-network evidence and check carrier/airport composition before transferring findings to a different operation.','sql_url':'sql/analysis/carrier_cohorts.sql'})
    report={'tables':tables,'findings':findings,'scope':'WN domestic reporting-carrier flights, 2023; eight focal airports. A separate January all-reporting-carrier aggregate supplies carrier-selection context. No passenger or international-leg inference.','missingness_policy':'No filling missing delays with zero; incomplete next-2h labels remain null. Cancellation is a distinct event, not zero delay.','sql_files':[str(p.relative_to(ROOT)) for p in sorted((ROOT/'sql/analysis').glob('*.sql'))]}
    (out/'eda.json').write_text(json.dumps(report,indent=2,default=str,allow_nan=False)+'\n')
    text=['# CASCADE: SQL investigation','',report['scope'],'',report['missingness_policy'],'']
    for f in findings:
      text.extend(['## '+f['title'],'']+[f'**{k.capitalize()}:** {f[k]}'+'\n' for k in ['question','denominator','finding','limitation','decision']]+[f"Generating SQL: [{f['sql_url']}](../{f['sql_url']})",''])
    text.extend(['## Selection, censoring and negative evidence','','All-carrier monthly source counts and WN scoped counts are reconciled in the source manifest. The eight-airport subset is compared with other WN origins in `monthly.sql`. Forecasting uses one carrier; the separate January carrier/airport benchmark diagnoses selection bias without isolating carrier effects. Local-hour/weekday/month cohorts are explicit in `local_seasonality.sql`.','', 'Weather groups include missing/stale observations. Rotations exclude airport discontinuity, cancelled/diverted legs, overlaps, missing actual times and scheduled turns outside 20–360 minutes. These filters select completed operations, so chain associations do not describe the worst censored disruptions. The path examples are plausible chains, not proven delay transmission.','', '## Complete rerunnable tables',''])
    for name,rows in tables.items():
      text += [f'### {name}', '',f'Query: [`{name}.sql`](../sql/analysis/{name}.sql). Full result: [`eda.json`](eda.json).', '', '```json',json.dumps(rows[:25],indent=2,default=str),'```','']
    (out/'EDA.md').write_text('\n'.join(text))
    # A static HTML chart report carries the same denominator and caveats as the data.
    body=[]
    for i,f in enumerate(findings):
      if i==0: bars=[(r['airport'],rate(r)) for r in a];suffix='%'
      elif i==1:bars=[(r['cohort'],100*r['outbound_late_rate']) for r in rot.values()];suffix='%'
      elif i==2: bars=[('median',overview['median_dep_delay']),('mean',overview['mean_dep_delay']),('p99',overview['p99_dep_delay'])];suffix=' min'
      elif i==3:bars=[(r['weather_group'],rate(r)) for r in weather];suffix='%'
      else:bars=[(k,100*v/carrier_total) for k,v in sorted(carrier_counts.items(),key=lambda x:-x[1])];suffix='%'
      maxv=max(v for _,v in bars) or 1
      chart=''.join(f'<div class="bar"><span>{html.escape(str(label))}</span><i style="width:{max(0,v)/maxv*65:.1f}%"></i><b>{v:.1f}{suffix}</b></div>' for label,v in bars)
      body.append('<section><h2>'+html.escape(f['title'])+'</h2><p>'+html.escape(f['question'])+'</p>'+chart+''.join('<p><strong>'+k.capitalize()+': </strong>'+html.escape(f[k])+'</p>' for k in ['denominator','finding','limitation','decision'])+'</section>')
    (out/'eda.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CASCADE · Evidence</title><style>body{margin:40px auto;max-width:1000px;padding:20px;background:#f3f1e9;color:#102e3c;font:16px system-ui}section{border-top:1px solid #a8b5b8;padding:24px 0}.bar{display:flex;align-items:center;gap:12px;height:36px}.bar span{width:220px;font-size:13px}.bar i{background:#167a7c;height:16px}.bar b{font-size:13px}p{line-height:1.6}</style><h1>CASCADE / Evidence notebook</h1><p>Rerunnable SQL investigation · WN / 2023</p>'+''.join(body)+'</html>')
    con.close();return report
if __name__=='__main__':run()
