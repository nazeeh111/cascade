"""One offline quickstart, one real-data full rebuild, and inspectable steps."""
import argparse,hashlib,json,os
from pathlib import Path
from .ingest import ROOT

def main():
    p=argparse.ArgumentParser(description='CASCADE: real-data SQL warehouse, forecasts and bounded recovery replay')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['warehouse','eda','model','simulate','benchmark','export','package-sample','verify']:
        sub.add_parser(name)
    ing=sub.add_parser('ingest',help='Download/hash-verify public partitions; completed partitions resume')
    ing.add_argument('--refresh',action='store_true',help='Re-download sources, preserving corrected prior partition bytes in data/history')
    q=sub.add_parser('quickstart',help='Build/test warehouse from bundled real subset, without network downloads')
    q.add_argument('--db',type=Path,default=ROOT/'data/quickstart.duckdb')
    f=sub.add_parser('full',help='Rebuild the entire source-to-app pipeline')
    f.add_argument('--skip-ingest',action='store_true')
    s=sub.add_parser('serve',help='Serve the frozen real-data replay app locally')
    s.add_argument('--port',type=int,default=8765)
    args=p.parse_args();os.chdir(ROOT)
    if args.command=='serve':
        from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
        from functools import partial
        print(f'CASCADE replay: http://127.0.0.1:{args.port}',flush=True)
        ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(ROOT/'web/dist'))).serve_forever();return
    if args.command=='quickstart':
        from .warehouse import run
        for f in (ROOT/'data/quickstart').glob('**/*.parquet'):
            item=next(s for s in json.loads((ROOT/'data/quickstart/manifest.json').read_text())['sources'] if s['path']==str(f.relative_to(ROOT)))
            if hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:raise ValueError(f'Changed bundled data: {f.name}')
        print(json.dumps(run(quickstart=True,db_path=args.db),indent=2));return
    steps=['ingest','warehouse','eda','model','simulate','benchmark','export','package-sample','verify'] if args.command=='full' else [args.command]
    if getattr(args,'skip_ingest',False):steps.remove('ingest')
    for step in steps:
        print(f'CASCADE / {step}',flush=True)
        if step=='ingest':from .ingest import run
        elif step=='warehouse':from .warehouse import run
        elif step=='eda':from .eda import run
        elif step=='model':from .modeling import run
        elif step=='simulate':from .simulation import run
        elif step=='benchmark':from .benchmark import run
        elif step=='export':from .export import run
        elif step=='package-sample':from .quickstart import package as run
        elif step=='verify':from .verify import run
        result=run(force=True) if step=='ingest' and getattr(args,'refresh',False) else run()
        if isinstance(result,dict) and step not in ['eda','model','simulate','benchmark','package-sample','export']:print(json.dumps(result,indent=2,default=str))
if __name__=='__main__':main()
