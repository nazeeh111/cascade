"""Fingerprint buildless browser assets so an updated release cannot reuse stale CSS/JS."""
from pathlib import Path
import hashlib
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'web/dist/index.html'

def versioned_index(source):
    for filename, attribute in [('styles.css', 'href'), ('app.js', 'src')]:
        digest = hashlib.sha256((ROOT / 'web/dist' / filename).read_bytes()).hexdigest()[:12]
        pattern = rf'{attribute}="{re.escape(filename)}(?:\?[^\"]*)?"'
        source, count = re.subn(pattern, f'{attribute}="{filename}?v={digest}"', source)
        if count != 1:
            raise ValueError(f'Expected one {filename} reference, found {count}')
    return source

if __name__ == '__main__':
    source = INDEX.read_text()
    updated = versioned_index(source)
    if '--check' in sys.argv:
        if source != updated:
            raise SystemExit('Browser asset fingerprints are stale. Run python scripts/version_web_assets.py')
    else:
        INDEX.write_text(updated)
    print('Browser asset fingerprints verified.')
