import json
from pathlib import Path
from cascade import ingest

def test_correction_preserves_verified_prior_partition_and_manifest(tmp_path,monkeypatch):
    monkeypatch.setattr(ingest,'ROOT',tmp_path)
    out=tmp_path/'data/processed/flights/year=2023/month=01/flights.parquet'
    out.parent.mkdir(parents=True);out.write_bytes(b'old real source snapshot')
    marker=out.with_suffix('.manifest.json');old_hash=ingest.sha(out)
    ingest.atomic_json(marker,{'parquet_sha256':old_hash,'scope':'WN'})
    part=out.with_suffix('.part');part.write_bytes(b'corrected source snapshot')
    ingest.promote_partition(part,out,marker)
    backup=tmp_path/'data/history/flights/year=2023/month=01'/old_hash/out.name
    assert ingest.sha(backup)==old_hash
    assert json.loads(backup.with_suffix('.manifest.json').read_text())['parquet_sha256']==old_hash
    assert out.read_bytes()==b'corrected source snapshot'
    # Restoring to a separate destination reproduces actual prior bytes.
    recovery=tmp_path/'recovery.parquet';recovery.write_bytes(backup.read_bytes())
    assert ingest.sha(recovery)==old_hash


def test_incomplete_marker_does_not_claim_a_resumable_partition(tmp_path):
    out=tmp_path/'flights.parquet';out.write_bytes(b'valid bytes')
    marker=tmp_path/'flights.manifest.json';marker.write_text('{"truncated":')
    assert ingest.cached_partition(out,marker) is None
    ingest.atomic_json(marker,{'parquet_sha256':ingest.sha(out)})
    assert ingest.cached_partition(out,marker) is not None
    out.write_bytes(b'tampered/incomplete bytes')
    assert ingest.cached_partition(out,marker) is None
