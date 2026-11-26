"""Verify the expected historical/current source boundary without rewriting evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
report = ROOT / 'reports/verification.json'
before = hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None

def invoke(*args):
    return subprocess.run([sys.executable, '-m', 'cascade.cli', 'verify', *args],
                          cwd=ROOT, text=True, capture_output=True)

strict = invoke()
if strict.returncode != 1 or strict.stderr.rstrip().splitlines()[-1:] != ['AssertionError: scenario_code_fingerprint: None']:
    raise SystemExit('Expected strict verification to reject the historical/current scenario source mismatch.')
historical = invoke('--historical-scenarios')
if historical.returncode:
    raise SystemExit('Historical verification failed: ' + historical.stderr)
try:
    data = json.loads(historical.stdout.split('\n', 1)[1])
except (IndexError, json.JSONDecodeError) as error:
    raise SystemExit('Historical verification returned malformed output.') from error
if not (data.get('passed') is True and data.get('scope') == 'historical_scenarios_only'
        and data.get('current_source_compatible') is False and data.get('full_database_checked') is False
        and data.get('checks') == 507):
    raise SystemExit('Historical verification scope or checks changed: ' + str(data))
after = hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None
if after != before:
    raise SystemExit('Verification unexpectedly changed the retained report.')
state = 'existing report preserved' if before is not None else 'report remained absent'
print(f'PASS: current-source mismatch refused; 507 historical-only checks passed; {state}.')
