"""The documented full rebuild must invoke source ingestion and every downstream stage."""
import sys,types
import pytest
from cascade import cli,ingest

@pytest.mark.parametrize('skip',[False,True])
def test_full_rebuild_routes_all_required_stages(monkeypatch,skip):
    seen=[]
    monkeypatch.setattr(ingest,'run',lambda **kw:seen.append('ingest'))
    for module,step,attribute in [('warehouse','warehouse','run'),('eda','eda','run'),('modeling','model','run'),('simulation','simulate','run'),('benchmark','benchmark','run'),('export','export','run'),('quickstart','package-sample','package'),('verify','verify','run')]:
        fake=types.ModuleType('cascade.'+module)
        setattr(fake,attribute,lambda s=step:seen.append(s))
        monkeypatch.setitem(sys.modules,'cascade.'+module,fake)
    monkeypatch.setattr(sys,'argv',['cascade','full']+(['--skip-ingest'] if skip else []))
    cli.main()
    expected=['ingest','warehouse','eda','model','simulate','benchmark','export','package-sample','verify']
    assert seen==(expected[1:] if skip else expected)
