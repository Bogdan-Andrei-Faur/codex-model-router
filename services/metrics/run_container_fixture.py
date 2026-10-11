"""Isolated image/HTTP/pg_dump restore proof; never uses a live Sentinel project."""
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid

root=Path(__file__).resolve().parents[2]
prefix='router-metrics-image-fixture-'+uuid.uuid4().hex[:10]
image='router-metrics:fixture-20261011'
env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_hex(32),ADMIN_PASSWORD=secrets.token_hex(32),DELETION_LEDGER='/data/deletions.jsonl')
env['DATABASE_URL']='postgresql://postgres:'+env['POSTGRES_PASSWORD']+'@db:5432/router_metrics_fixture'
net,volume,db,api=(prefix+'-'+name for name in ('net','ledger','db','api'))

def run(args,**kw):
    return subprocess.run(['docker',*args],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)

def command(*args):
    return run(['run','--rm','--network',net,'-v',volume+':/data','-e','DATABASE_URL','-e','ADMIN_PASSWORD','-e','DELETION_LEDGER',image,'python','-m','services.metrics.app',*args])

try:
    run(['network','create',net]);run(['volume','create',volume])
    run(['run','-d','--name',db,'--network',net,'--network-alias','db','-e','POSTGRES_PASSWORD','-e','POSTGRES_DB=router_metrics_fixture','postgres:17-bookworm'])
    for _ in range(60):
        if subprocess.run(['docker','exec',db,'pg_isready','-U','postgres'],capture_output=True).returncode==0:break
        time.sleep(.5)
    else:raise RuntimeError('database_not_ready')
    command('migrate')
    run(['run','-d','--name',api,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--network',net,'-p','127.0.0.1::8080','-v',volume+':/data','-e','DATABASE_URL','-e','ADMIN_PASSWORD','-e','DELETION_LEDGER',image])
    port=run(['port',api,'8080/tcp']).stdout.decode().strip().rsplit(':',1)[1]
    base='http://127.0.0.1:'+port
    def request(path,body=None,authorization=None):
        headers={'Content-Type':'application/json'}
        if authorization:headers['Authorization']=authorization
        req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as response:return response.status,response.read()
        except urllib.error.HTTPError as error:
            try:return error.code,error.read()
            finally:error.close()
    for _ in range(40):
        try:
            if request('/health/ready')[0]==200:break
        except OSError:pass
        time.sleep(.25)
    else:raise RuntimeError('api_not_ready')
    assert request('/')[0]==401
    auth='Basic '+base64.b64encode(('owner:'+env['ADMIN_PASSWORD']).encode()).decode()
    assert request('/',authorization=auth)[0]==200
    identity=uuid.uuid4().hex;bearer='Bearer '+secrets.token_hex(32)
    assert request('/v1/enroll',{'installation':identity},bearer)[0]==200
    consent={'installation':identity,'epoch':1,'enabled':True,'prompts':False,'raw_otlp':False}
    assert request('/v1/consent',consent,bearer)[0]==200
    batch={'installation':identity,'epoch':1,'events':[{'id':uuid.uuid4().hex,'kind':'metrics','data':{'event':'decision_accepted'}}]}
    assert request('/v1/events',batch,bearer)[0]==200
    assert request('/v1/events',batch,bearer)[0]==200
    dump=run(['exec',db,'pg_dump','-U','postgres','-Fc','router_metrics_fixture']).stdout
    assert request('/v1/delete',{'installation':identity,'epoch':2},bearer)[0]==200
    # Restore the real pre-deletion archive to another isolated DB, then replay latest ledger.
    run(['exec',db,'createdb','-U','postgres','router_metrics_restored_fixture'])
    run(['exec','-i',db,'pg_restore','-U','postgres','-d','router_metrics_restored_fixture'],input=dump)
    before=run(['exec',db,'psql','-U','postgres','-d','router_metrics_restored_fixture','-tAc','SELECT COUNT(*) FROM events']).stdout.strip()
    assert before==b'1'
    env['DATABASE_URL']=env['DATABASE_URL'].replace('/router_metrics_fixture','/router_metrics_restored_fixture')
    command('replay-deletions')
    after=run(['exec',db,'psql','-U','postgres','-d','router_metrics_restored_fixture','-tAc','SELECT COUNT(*) FROM events']).stdout.strip()
    assert after==b'0'
    contents=run(['exec',api,'python','-c',"from pathlib import Path; assert not Path('/app/state').exists(); assert not Path('/app/config.local.json').exists(); print('image_private_inputs_absent')"]).stdout.decode().strip()
    print(json.dumps({'pass':True,'image_http':True,'read_only_container':True,'pg_dump_restore':True,'deletion_replay':True,'private_inputs_absent':contents=='image_private_inputs_absent','production':False}))
except subprocess.CalledProcessError as error:
    # Command environments and DB error details are private; safe fixture classification only.
    raise SystemExit('Container fixture command failed with exit code '+str(error.returncode)) from None
finally:
    for name in (api,db):subprocess.run(['docker','rm','-f',name],capture_output=True)
    subprocess.run(['docker','volume','rm',volume],capture_output=True)
    subprocess.run(['docker','network','rm',net],capture_output=True)
