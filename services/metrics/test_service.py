"""Requires isolated PostgreSQL. Never point these destructive fixtures at production."""
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.metrics.app import app, connect, migrate, replay_deletions
from codex_model_router.telemetry.central_client import CentralTelemetry, capture


@unittest.skipUnless(os.environ.get('METRICS_FIXTURE') == '1' and '/router_metrics_fixture' in os.environ.get('DATABASE_URL', ''), 'isolated PostgreSQL fixture required')
class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migrate()
        migrate()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'ADMIN_PASSWORD':'test-owner-'+'a'*40, 'DELETION_LEDGER':str(Path(self.temp.name)/'deletions.jsonl')})
        self.env.start()
        with connect() as db:
            db.execute('TRUNCATE events,installations,deletions')
        self.api = TestClient(app, raise_server_exceptions=False)
        self.installation = 'a'*32
        self.token = '1'*64
        self.base = {'installation':self.installation,'epoch':1}
        self.owner = {'Authorization':'Basic '+base64.b64encode(('owner:'+os.environ['ADMIN_PASSWORD']).encode()).decode()}

    def tearDown(self):
        self.api.close()
        self.env.stop()
        self.temp.cleanup()

    def post(self,path,body,token=None):
        return self.api.post('/v1/'+path,json=body,headers={'Authorization':'Bearer '+(token or self.token)})

    def enroll(self,**flags):
        self.assertEqual(self.post('enroll',{'installation':self.installation}).status_code,200)
        response=self.post('consent',self.base|{'enabled':True,'prompts':False,'raw_otlp':False}|flags)
        self.assertEqual(response.status_code,200,response.text)

    def event(self,kind='metrics',data=None,identifier='e'*32):
        return {'id':identifier,'kind':kind,'data':data or {'event':'decision_accepted','model':'gpt-6.1-sol'}}

    def test_health_and_private_panel(self):
        self.assertEqual(self.api.get('/health/ready').status_code,200)
        self.assertEqual(self.api.get('/').status_code,401)
        self.assertEqual(self.api.get('/',headers={'Authorization':'Bearer '+self.token}).status_code,401)
        response=self.api.get('/',headers=self.owner)
        self.assertEqual(response.status_code,200)
        self.assertIn('no-store',response.headers['cache-control'])
        self.assertIn('Desconocido',response.text)

    def test_dedup_and_conflicting_identity(self):
        self.enroll()
        batch=self.base|{'events':[self.event()]}
        self.assertEqual(self.post('events',batch).status_code,200)
        self.assertEqual(self.post('events',batch).status_code,200)
        with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)
        batch['events'][0]['data']['time']=5
        self.assertEqual(self.post('events',batch).status_code,409)
        self.assertEqual(self.post('events',batch,token='2'*64).status_code,401)

    def test_diagnostic_permissions_and_raw_roundtrip(self):
        self.enroll()
        raw=' {"resourceLogs": [], "synthetic": "<script>text</script>"} '
        event=self.event('raw_otlp',raw)
        self.assertEqual(self.post('events',self.base|{'events':[event]}).status_code,403)
        self.base['epoch']=2
        self.post('consent',self.base|{'enabled':True,'prompts':False,'raw_otlp':True})
        self.assertEqual(self.post('events',self.base|{'events':[event]}).status_code,200)
        path='/admin/diagnostic/'+self.installation+'/'+event['id']
        self.assertEqual(self.api.get(path).status_code,401)
        response=self.api.get(path,headers=self.owner)
        self.assertEqual(response.json(),raw)
        self.assertIn('attachment',response.headers['content-disposition'])
        self.assertNotIn('<script>text',self.api.get('/',headers=self.owner).text)

    def test_revoke_consent_rejects_old_inflight_epoch(self):
        self.enroll(prompts=True)
        self.post('consent',self.base|{'epoch':2,'enabled':False,'prompts':False,'raw_otlp':False})
        self.assertEqual(self.post('events',self.base|{'events':[self.event()]}).status_code,409)
        with connect() as db: db.execute('UPDATE installations SET revoked=true')
        self.assertEqual(self.post('enroll',{'installation':self.installation}).status_code,401)

    def test_delete_ledger_replays_after_restore_and_allows_new_permission(self):
        self.enroll()
        self.post('events',self.base|{'events':[self.event()]})
        with connect() as db:
            old=db.execute('SELECT installation,id,epoch,kind,data,size FROM events').fetchone()
        self.assertEqual(self.post('delete',self.base|{'epoch':2}).status_code,200)
        with connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
            from psycopg.types.json import Jsonb
            db.execute('INSERT INTO events(installation,id,epoch,kind,data,size) VALUES(%s,%s,%s,%s,%s,%s)',(*old[:4],Jsonb(old[4]),old[5]))
            db.execute('UPDATE installations SET epoch=1,enabled=true')
            db.execute('TRUNCATE deletions')
        replay_deletions()
        with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
        self.assertEqual(self.post('events',self.base|{'events':[self.event()]}).status_code,409)
        newer=self.base|{'epoch':3,'enabled':True,'prompts':True,'raw_otlp':False}
        self.assertEqual(self.post('consent',newer).status_code,200)
        event=self.event('prompts',{'prompt':'new consent','decision_id':'f'*32})
        self.assertEqual(self.post('events',self.base|{'epoch':3,'events':[event]}).status_code,200)
        replay_deletions()
        # Replaying an old deletion must not revoke a later consent or erase its data.
        self.assertEqual(self.post('consent',newer).status_code,200)
        with connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)

    def test_caps_atomic_rejection_and_enrollment_rate(self):
        self.enroll()
        with patch.dict(os.environ,{'MAX_INSTALLATION_BYTES':'1'}):
            self.assertEqual(self.post('events',self.base|{'events':[self.event()]}).status_code,507)
        with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
        with patch.dict(os.environ,{'ENROLLMENTS_PER_HOUR':'1'}):
            self.assertEqual(self.post('enroll',{'installation':'b'*32}).status_code,429)
        self.assertEqual(self.api.post('/v1/enroll',content=b'x'*1048577,headers={'Content-Type':'application/json'}).status_code,413)
        self.assertEqual(self.api.post('/v1/enroll',content=b'x',headers={'Content-Type':'application/json','Content-Encoding':'gzip'}).status_code,415)

    def test_cross_installation_cannot_delete_or_read(self):
        self.enroll()
        self.post('events',self.base|{'events':[self.event()]})
        self.assertEqual(self.post('enroll',{'installation':'b'*32},'2'*64).status_code,200)
        self.assertEqual(self.post('delete',self.base,'2'*64).status_code,401)
        with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)

    def test_client_to_database_retry_and_consent(self):
        stored={}
        def secret(root,value=None):
            if value: stored.update(value)
            return stored or None
        def send(path,body,token):
            response=self.api.post(path,json=body,headers={'Authorization':'Bearer '+token})
            if response.status_code!=200: raise OSError('fixture_rejected')
            return response.json()
        root=Path(self.temp.name)/'client'
        with patch.object(CentralTelemetry,'start'):
            client=CentralTelemetry(root,secret=secret,send=send)
            client.configure('enabled',True)
            capture(root,'metrics',{'event':'decision_accepted','thread':'synthetic-secret','model':'gpt-6.1-sol'})
            def lost_ack(path,body,token):
                result=send(path,body,token)
                if path.endswith('events'): raise OSError('lost_ack')
                return result
            client.send=lost_ack
            with self.assertRaises(OSError): client.tick()
            client.send=send
            client.tick()
            with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],1)
            self.assertEqual(client.snapshot()['pending'],0)
            client.configure('enabled',False); client.tick()
            client.configure('enabled',True); client.configure('prompts',True)
            capture(root,'prompts',{'decision_id':'fixture','prompt':'synthetic message'})
            client.tick()
            client.configure('delete',True); client.tick()
            with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)

    def test_bad_metrics_transaction_never_persists_partial_batch(self):
        self.enroll()
        bad=self.event(data={'event':'decision_accepted','prompt':'not allowed'},identifier='f'*32)
        response=self.post('events',self.base|{'events':[self.event(),bad]})
        self.assertEqual(response.status_code,400)
        with connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0)
