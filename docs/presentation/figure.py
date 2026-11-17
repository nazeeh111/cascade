from pathlib import Path
import json,html,hashlib
p=Path(__file__).parent;d=json.loads((p/'receipt.json').read_text());a=d['airport']
for mobile in [False,True]:
 w,h=(375,840)if mobile else(1120,560);pad=22 if mobile else 36;parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">A forecast is not hindsight. A scenario is not a saving.</title><desc id="desc">Denver on 19 October 2023 at 16:00 UTC. The frozen model predicted 30.4 percent disruption among 28 scheduled departures. The later final rate was 53.6 percent. The separate fixed 16:00 UTC recovery experiment reported 42.5 hypothetical minutes, not measured savings. All bar lengths use a shared zero to 100 percent scale.</desc><rect width="{w}" height="{h}" fill="#f5f3eb"/>']
 def text(x,y,t,size=16,color='#17313b',font='Arial, Helvetica, sans-serif'):parts.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}">{html.escape(str(t))}</text>')
 text(pad,32,'CASCADE / ONE CUTOFF, THREE CLAIMS',11,'#526b70')
 for i,line in enumerate(['A forecast is not hindsight.','A scenario is not a saving.'] if mobile else['A forecast is not hindsight. A scenario is not a saving.']):text(pad,76+i*34,line,26 if mobile else 36)
 text(pad,166 if mobile else 116,'DEN · 19 OCT 2023 · 16:00 UTC · 28 departures',11 if mobile else 16)
 y=204 if mobile else 165;text(pad,y,'01 / WHAT WAS AVAILABLE AT CUTOFF',11,'#526b70')
 for i,line in enumerate(['Latest event available: 15:59 UTC','Weather eligible: 16:00 UTC','Declared event/weather lags: 15/60 min']):text(pad,y+27+i*23,line,13 if mobile else 16)
 chartY=345 if mobile else 305;bw=w-pad*2;track=(bw-110) if mobile else 440
 for i,(name,key,color)in enumerate([('Forecast','prediction','#17313b'),('Later outcome','target_rate','#b45c35')]):
  yy=chartY+i*64;text(pad,yy,name,16);text(w-pad-70 if mobile else pad+track+20,yy,f'{a[key]*100:.1f}%',18)
  parts.append(f'<rect x="{pad}" y="{yy+12}" width="{track}" height="10" fill="#dddcd2"/><rect data-key="{key}" x="{pad}" y="{yy+12}" width="{track*a[key]:.10f}" height="10" fill="{color}"/>')
 text(pad,chartY+126,'Shared scale: 0–100% · late ≥15min or cancelled',11,'#526b70')
 y=547 if mobile else 183;x=pad if mobile else 690
 text(x,y,'02 / SEPARATE SIMULATION',11,'#526b70');text(x,y+39,'42.5 hypothetical minutes',21)
 lines=['4 bounded teams · DEN 2 / LAS 2','Fixed 16:00 UTC, not cursor dependent.','Actual-tail topology uses hindsight.','Held-out baseline late15 recall: 11.2%.','Not causal savings or staffing advice.']
 for i,line in enumerate(lines):text(x,y+71+i*25,line,12 if mobile else 14)
 fy=779 if mobile else 508;text(pad,fy,'The final label was available on 20 Oct at 06:00 UTC.',11 if mobile else 14);text(pad,fy+23,'Frozen historical outputs. No new model or simulator run.',11 if mobile else 14)
 parts.append('</svg>');(p/('cutoff-mobile.svg'if mobile else'cutoff.svg')).write_text(''.join(parts))
(p/'figure-manifest.json').write_text(json.dumps({'input':'receipt.json','inputSHA256':hashlib.sha256((p/'receipt.json').read_bytes()).hexdigest(),'bars':{'prediction':a['prediction'],'target_rate':a['target_rate']},'mapping':'width=track*rate; track=221phone/440desktop; shared zero-to100percent scale within each variant','timeMeaning':'No measured time axis. All clock labels explicitly UTC; later label remains after cutoff.','simulationMeaning':'Archived selected policy, rounded42.4639505937339minutes; not recomputed/causal.'},indent=2)+'\n')
