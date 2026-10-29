"""Copy tracked buildless sources into Sites' supported static deployment directory."""
from pathlib import Path
import hashlib
import os
import shutil
import tempfile
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'web/dist'
from version_web_assets import versioned_index
index_source=(source/'index.html').read_text()
if index_source != versioned_index(index_source):
    raise ValueError('Browser asset fingerprints are stale. Run python scripts/version_web_assets.py')
required=['index.html','app.js','styles.css','data/replay.json']
for name in required:
    if not (source/name).is_file():raise FileNotFoundError(name)
with tempfile.TemporaryDirectory(prefix='cascade-static-',dir=ROOT) as temp:
    stage=Path(temp)/'dist';shutil.copytree(source,stage)
    if (stage/'qa-responsive.html').exists():raise ValueError('Disposable QA wrapper cannot be published')
    for p in source.rglob('*'):
        if p.is_file() and hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256((stage/p.relative_to(source)).read_bytes()).digest():raise ValueError(f'Copy mismatch: {p.name}')
    destination=ROOT/'dist';backup=ROOT/'dist-previous'
    if backup.exists():
        # Both directories are generated solely by this script, never editable source.
        if not (backup/'.cascade-generated').exists():raise ValueError('Unrecognized backup; preserve it')
        shutil.rmtree(backup)
    if destination.exists():
        if not (destination/'.cascade-generated').exists():raise ValueError('Unrecognized dist directory; preserve it')
        os.replace(destination,backup)
    (stage/'.cascade-generated').write_text('Derived only from tracked web/dist source. Rebuild with scripts/build_site.py.\n')
    os.replace(stage,destination)
    if backup.exists():shutil.rmtree(backup)
print('CASCADE static package: dist/ (source bytes verified)')
