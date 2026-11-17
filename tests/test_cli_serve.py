"""The printed loopback route must reach the actual ephemeral HTTP server."""
import os,queue,re,subprocess,sys,threading
from pathlib import Path
from urllib.request import urlopen

def test_serve_ephemeral_port_prints_the_bound_reachable_route():
    root=Path(__file__).resolve().parents[1]
    process=subprocess.Popen([sys.executable,'-m','cascade.cli','serve','--port','0'],cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    lines=queue.Queue()
    threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
    try:
        line=lines.get(timeout=15)
        address=re.search(r'http://127\.0\.0\.1:(\d+)',line)
        assert address is not None,line
        assert int(address.group(1))>0,'The printed route must use the bound port, not the requested port zero.'
        with urlopen(address.group(0),timeout=5) as response:
            assert response.status==200
            assert b'Cascade' in response.read()
    finally:
        process.terminate()
        try:process.communicate(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.communicate()
