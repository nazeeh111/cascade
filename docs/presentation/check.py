"""Standard-library integrity and stored-evidence reader, not a forecast rerun."""
from pathlib import Path
import json,hashlib,csv,xml.etree.ElementTree as ET
p=Path(__file__).parent;m=json.loads((p/'MANIFEST.json').read_text())
for name,digest in m['sha256'].items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
r=json.loads((p/'receipt.json').read_text());d=json.loads((p/'app/data/replay.json').read_text());assert hashlib.sha256((p/'app/data/replay.json').read_bytes()).hexdigest()==r['frozen_replay_sha256']
day=next(x for x in d['days']if x['date']==r['day']);f=next(x for x in day['frames']if x['cutoff']==r['cutoff']);a=next(x for x in f['airports']if x['airport']==r['airport']['airport']);assert a==r['airport'];assert day['scenarios']==r['scenarios'];assert a['scheduled']==28;assert abs(a['target_rate']*28-15)<1e-12
j=json.loads((p/'continuity.json').read_text());row=list(csv.DictReader((p/'continuity.csv').open()))[0];assert {k:str(v)for k,v in j.items()}==row
for name,track in [('cutoff.svg',440),('cutoff-mobile.svg',221)]:
 root=ET.parse(p/name).getroot();bars=[x for x in root.iter()if 'data-key'in x.attrib];assert len(bars)==2
 for b in bars:assert abs(float(b.attrib['width'])-track*a[b.attrib['data-key']])<1e-8
print(f"Verified {len(m['sha256'])} exact payloads, selected frozen frame/scenarios, native CSV/JSON and shared-scale bars. Stored evidence only; no science rerun.")
