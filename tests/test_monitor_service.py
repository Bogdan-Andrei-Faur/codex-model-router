"""Real private child-pipe protocol, safe projection, lazy history and actions."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.monitor.monitor_service import dispatch, serve, MAX_REQUEST
from codex_model_router.monitor.monitor_state import MonitorState, TELEMETRY_COUNTERS
from codex_model_router.storage.state_store import atomic_json

ROOT = Path(__file__).resolve().parents[1]


class MonitorServiceTests(unittest.TestCase):
    def test_prepared_connection_has_persistent_restart_notice_until_bridge_is_observed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);atomic_json(root/'config.local.json',{})
            model=MonitorState(root,ROOT,platform='windows')
            try:
                self.assertFalse(model.payload(False)['desktopRestartPending'])
                atomic_json(root/'state/desktop-integration.json',{'status':'registered','wrapper':'PRIVATE_PATH'})
                prepared=model.payload(False)
                self.assertTrue(prepared['desktopRestartPending']);self.assertTrue(prepared['restartRequired'])
                self.assertNotIn('PRIVATE_PATH',json.dumps(prepared))
                atomic_json(root/'state/status-fixture.json',{'pid':os.getpid(),'heartbeat':time.time(),'threads':{}})
                observed=model.payload(False)
                self.assertFalse(observed['desktopRestartPending']);self.assertFalse(observed['restartRequired'])
            finally:model.close()
    def test_connection_feedback_uses_known_codes_without_echoing_stderr(self):
        cases = [('source_bridge_active','cierra Desktop'),('source_monitor_open','monitor de la instalación anterior'),
                 ('source_status_unreadable','leer el estado'),('source_connection_unverified','verificar la conexión')]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);atomic_json(root/'config.local.json',{})
            model=MonitorState(root,ROOT,platform='windows')
            try:
                for code,expected in cases:
                    result=subprocess.CompletedProcess([],1,b'',json.dumps({'code':code,'error':'PRIVATE_SENTINEL'}).encode())
                    with self.subTest(code=code), patch('codex_model_router.monitor.monitor_state.subprocess.run',return_value=result):
                        feedback=model.action({'action':'connection','value':'install'})
                    self.assertIn(expected,feedback);self.assertNotIn('PRIVATE_SENTINEL',feedback)
                for stderr in (b'PRIVATE_SENTINEL',b'[]',b'{"code":[],"error":"PRIVATE_SENTINEL"}',b'{"code":"unknown","error":"PRIVATE_SENTINEL"}'):
                    with patch('codex_model_router.monitor.monitor_state.subprocess.run',return_value=subprocess.CompletedProcess([],1,b'[]',stderr)):
                        feedback=model.action({'action':'connection','value':'install'})
                    self.assertEqual(feedback,'No se pudo completar la conexión. Tus tareas siguen abiertas.')
            finally:model.close()

    def test_three_platform_projections_share_counters_and_custody_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            atomic_json(root/'config.local.json', {'enabled':True,'jev':{'connection':'typesafe','api_key':'PRIVATE_SENTINEL'},'python':'PRIVATE_PATH'})
            atomic_json(root/'state/status-fixture.json', {'pid':os.getpid(),'heartbeat':time.time(),'threads':{'thread':{'updated':1,'status':'active'}},'agent_threads':{'thread':{'updated':1,'status':'active'},'idle':{'status':'idle','catalog_only':True}},'telemetry':dict.fromkeys(TELEMETRY_COUNTERS,1)})
            projections=[]
            for platform in ('macos','windows','linux'):
                payload=MonitorState(root, ROOT, platform=platform).payload(False)
                self.assertEqual(payload['platform'],platform)
                self.assertNotIn('history',payload)
                self.assertNotIn('PRIVATE_',json.dumps(payload))
                self.assertTrue(all(payload['telemetry'][key]==1 for key in set(TELEMETRY_COUNTERS)))
                self.assertEqual(payload['threads']['thread']['status'],'active')
                self.assertEqual(set(payload['threads']),{'thread'})
                self.assertEqual(set(payload['agentThreads']),{'thread','idle'})
                self.assertEqual(payload['taskModes']['idle'],'automatic')
                projections.append({key:payload[key] for key in ('threads','agentThreads','telemetry','config','connections')})
            self.assertEqual(projections[0],projections[1]); self.assertEqual(projections[1],projections[2])

    def test_real_child_lazy_history_revision_and_preview_are_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'state').mkdir()
            history=root/'state/history.jsonl';history.write_bytes(b'{"event":"decision_created","decision_id":"one","thread":"test"}\n')
            process=subprocess.Popen([sys.executable,str(ROOT/'monitor_service.py'),'--root',folder,'--code-root',str(ROOT),'--platform','macos','--preview'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                def request(identifier,**body):
                    process.stdin.write(json.dumps(dict(body,requestId=identifier)).encode()+b'\n');process.stdin.flush()
                    reply=json.loads(process.stdout.readline());self.assertEqual(reply['requestId'],identifier);return reply
                live=request(1,action='snapshot',history=False,revision=-1)['payload']
                self.assertNotIn('history',live);self.assertFalse(live['historyLoaded']);self.assertEqual(live['journalRevision'],0)
                loaded=request(2,action='snapshot',history=True,revision=-1)['payload']
                self.assertEqual(len(loaded['history']),1);revision=loaded['journalRevision']
                unchanged=request(3,action='snapshot',history=True,revision=revision)['payload'];self.assertNotIn('history',unchanged)
                with history.open('ab') as stream:stream.write(b'{"event":"decision_created","decision_id":"two"}\n')
                compact=request(4,action='snapshot',history=False,revision=revision)['payload'];self.assertEqual(compact['journalRevision'],revision)
                refreshed=request(5,action='snapshot',history=True,revision=revision)['payload'];self.assertEqual(len(refreshed['history']),2)
                self.assertFalse(request(6,action='config',key='enabled',value=False)['ok'])
                self.assertFalse(request(7,action='secret',value='PRIVATE_SENTINEL')['ok'])
                self.assertFalse(request(8,action='connection',value='install')['ok'])
                self.assertFalse(request(9,action='snapshot',history='true')['ok'])
                self.assertFalse((root/'config.local.json').exists())
                process.stdin.close();self.assertEqual(process.wait(timeout=10),0);self.assertEqual(process.stderr.read(),b'')
            finally:
                if process.poll() is None:process.kill();process.wait()
                process.stdout.close();process.stderr.close()

    def test_actions_keep_config_and_history_locks_and_validate_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);atomic_json(root/'config.local.json',{'enabled':True,'jev':{'api_key':'PRIVATE_SENTINEL'}})
            (root/'state').mkdir()
            (root/'state/history.jsonl').write_text('{"decision_id":"one","thread":"thread"}\n')
            model=MonitorState(root,ROOT,platform='windows')
            for action in ({'action':'config','key':'policy_mode','value':'compare'}, {'action':'taskMode','thread':'thread','value':'manual'}, {'action':'quality','id':'one','aspect':'model','value':'adequate'}):
                self.assertTrue(dispatch(model,dict(action,requestId=1))['ok'])
            self.assertEqual(json.loads((root/'config.local.json').read_text())['jev']['api_key'],'PRIVATE_SENTINEL')
            self.assertEqual(model.payload()['taskModes']['thread'],'manual')
            self.assertEqual(model.payload()['history'][-1]['record']['model_quality'],'adequate')
            for action in ({'action':'quality','id':'missing','value':'adequate'}, {'action':'taskMode','thread':'unknown','value':'manual'}, {'action':'config','key':'python','value':'evil'}, {'action':'connection','value':'arbitrary'}):
                with self.assertRaises(ValueError):dispatch(model,dict(action,requestId=2))

    def test_real_child_preserves_decision_id_separately_from_request_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'state').mkdir()
            (root/'state/history.jsonl').write_text('{"decision_id":"decision-one","thread":"thread"}\n')
            command=[sys.executable,str(ROOT/'monitor_service.py'),'--root',folder,'--code-root',str(ROOT),'--platform','windows']
            message={'action':'quality','id':'decision-one','requestId':17,'aspect':'effort','value':'adequate'}
            result=subprocess.run(command,input=json.dumps(message).encode()+b'\n',capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0)
            self.assertEqual(json.loads(result.stdout)['requestId'],17)
            self.assertTrue(json.loads(result.stdout)['ok'])
            row=json.loads((root/'state/history.jsonl').read_text().splitlines()[-1])
            self.assertEqual(row['decision_id'],'decision-one')
            self.assertEqual(row['effort_quality'],'adequate')

    def test_invalid_or_oversized_frames_never_echo_private_input(self):
        with tempfile.TemporaryDirectory() as folder:
            model=MonitorState(folder,ROOT)
            source=io.BytesIO(b'not-json-PRIVATE_SENTINEL\n'+b'{"requestId":true,"action":"snapshot"}\n')
            output=io.BytesIO();serve(model,source,output)
            self.assertNotIn(b'PRIVATE_',output.getvalue())
            self.assertTrue(all(not json.loads(line)['ok'] for line in output.getvalue().splitlines()))
            output=io.BytesIO();serve(model,io.BytesIO(b'x'*(MAX_REQUEST+1)),output);self.assertEqual(output.getvalue(),b'')


if __name__ == '__main__': unittest.main()
