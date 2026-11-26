"""Historical evidence is opt-in and never turns current compatibility green."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

SOURCE = Path(__file__).resolve().parents[1]

@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'checkout'
    shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (root / 'reports/verification.json').write_text('original report sentinel\n')
    return root

def command(root, *args):
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, '-B', '-m', 'cascade.cli', 'verify', *args], cwd=root, env=env, capture_output=True, text=True)

def test_historical_is_explicit_and_never_overwrites_report(checkout):
    result = command(checkout, '--historical-scenarios')
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.split('\n', 1)[1])
    assert payload['scope'] == 'historical_scenarios_only'
    assert payload['current_source_compatible'] is False
    assert payload['full_database_checked'] is False
    assert payload['checks'] == 507
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'

def test_default_still_rejects_current_mismatch_without_overwrite(checkout):
    result = command(checkout)
    assert result.returncode != 0
    assert 'scenario_code_fingerprint' in result.stderr
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'

def test_tampered_snapshot_rejected(checkout):
    path = checkout / 'evidence/historical/simulation.py.txt'
    data = bytearray(path.read_bytes()); data[0] ^= 1; path.write_bytes(data)
    result = command(checkout, '--historical-scenarios')
    assert result.returncode != 0
    assert 'historical snapshot identity mismatch' in result.stderr
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'

def test_wrong_scenario_source_rejected(checkout):
    path = checkout / 'reports/scenarios.json'
    report = json.loads(path.read_text()); report['implementation_sha256'] = '0' * 64
    path.write_text(json.dumps(report))
    result = command(checkout, '--historical-scenarios')
    assert result.returncode != 0
    assert 'scenario_code_fingerprint' in result.stderr
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'

def test_symlink_snapshot_refused(checkout):
    path = checkout / 'evidence/historical/simulation.py.txt'
    copy = path.with_suffix('.copy'); path.rename(copy); path.symlink_to(copy.name)
    result = command(checkout, '--historical-scenarios')
    assert result.returncode != 0
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'

def test_symlink_parent_refused(checkout):
    directory = checkout / 'evidence/historical'
    moved = directory.with_name('historical-copy'); directory.rename(moved)
    directory.symlink_to(moved.name, target_is_directory=True)
    result = command(checkout, '--historical-scenarios')
    assert result.returncode != 0
    assert (checkout / 'reports/verification.json').read_text() == 'original report sentinel\n'
