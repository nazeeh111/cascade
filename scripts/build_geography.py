"""Build CASCADE's static CONUS map from pinned Census-derived US Atlas data.

Only presentation geometry changes. Airport/data projection matches app.js.
"""
from pathlib import Path
import hashlib,json,html,requests
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'web/dist/assets'
URL='https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json'
LICENSE='https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/LICENSE'
def build():
    response=requests.get(URL,timeout=60);response.raise_for_status();raw=response.content;topology=response.json()
    license_response=requests.get(LICENSE,timeout=60);license_response.raise_for_status();assert 'permission' in license_response.text.lower()
    scale=topology['transform']['scale'];translate=topology['transform']['translate'];arcs=[]
    for encoded in topology['arcs']:
        x=y=0;decoded=[]
        for dx,dy in encoded:
            x+=dx;y+=dy;decoded.append((x*scale[0]+translate[0],y*scale[1]+translate[1]))
        arcs.append(decoded)
    def ring(indices):
        points=[]
        for idx in indices:
            segment=arcs[idx] if idx>=0 else list(reversed(arcs[~idx]))
            points.extend(segment if not points else segment[1:])
        return points
    def path(indices):
        points=ring(indices)
        return 'M'+'L'.join(f'{65+(lon+126)/58*770:.1f},{365-(lat-25)/24*300:.1f}' for lon,lat in points)+'Z'
    states=[]
    for g in topology['objects']['states']['geometries']:
        if int(g['id']) in {2,15,60,66,69,72,78}:continue
        polygons=[g['arcs']] if g['type']=='Polygon' else g['arcs']
        d=''.join(path(r) for polygon in polygons for r in polygon)
        states.append(f'<path d="{d}"><title>{html.escape(g["properties"]["name"])}</title></path>')
    assert len(states)==49
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 445"><defs><linearGradient id="land" x2="1" y2="1"><stop stop-color="#2b5059"/><stop offset="1" stop-color="#1a3c46"/></linearGradient></defs><g fill="url(#land)" fill-rule="evenodd" stroke="#709698" stroke-opacity=".48" stroke-width=".65" stroke-linejoin="round">'+''.join(states)+'</g></svg>'
    ASSETS.mkdir(exist_ok=True);(ASSETS/'us-states.svg').write_text(svg);(ASSETS/'US-Atlas-LICENSE.txt').write_bytes(license_response.content)
    info={'source':URL,'upstream':'https://github.com/topojson/us-atlas','input_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(svg.encode()).hexdigest(),'license':'ISC','basis':'US Census Bureau cartographic boundary data, 2017 edition','scope':'48 contiguous states and District of Columbia; background presentation geometry only','projection':'Same equirectangular lon/lat transform as airport positions in app.js','state_geometries':len(states)}
    (ASSETS/'geography-provenance.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps({'geographies':len(states),'svg_bytes':len(svg.encode())}))
if __name__=='__main__':build()
