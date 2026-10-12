"""Run real PostgreSQL integration in an isolated, owned disposable container."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

root=Path(__file__).resolve().parents[2]
name='router-metrics-fixture-'+uuid.uuid4().hex[:10]
env={k:v for k,v in os.environ.items() if not k.startswith(('PERSONAL_CODEX_','_PYI_','_MEIPASS','DYLD_')) and k not in ('PYTHONHOME','VIRTUAL_ENV')}
env['POSTGRES_PASSWORD']=secrets.token_hex(24)
env['PYTHONPATH']=str(root/'src')+os.pathsep+str(root)
try:
    subprocess.run(['docker','run','--detach','--rm','--name',name,'-e','POSTGRES_PASSWORD','-e','POSTGRES_DB=router_metrics_fixture','-p','127.0.0.1::5432','postgres:17-bookworm'],env=env,check=True,stdout=subprocess.DEVNULL)
    for _ in range(60):
        # The entrypoint's temporary Unix-socket server precedes TCP readiness.
        result=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],capture_output=True)
        if result.returncode==0: break
        time.sleep(.5)
    else: raise RuntimeError('fixture_database_not_ready')
    port=subprocess.check_output(['docker','port',name,'5432/tcp'],text=True).strip().rsplit(':',1)[1]
    env['DATABASE_URL']='postgresql://postgres:'+env.pop('POSTGRES_PASSWORD')+'@127.0.0.1:'+port+'/router_metrics_fixture'
    env['METRICS_FIXTURE']='1'
    raise SystemExit(subprocess.call([sys.executable,'-m','unittest','services.metrics.test_service','-v'],cwd=root,env=env))
finally:
    subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
