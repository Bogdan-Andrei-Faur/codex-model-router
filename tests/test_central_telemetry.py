"""Synthetic fixtures only: consent, durable replay, limits and privacy boundaries."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_model_router.telemetry.central_client import CentralTelemetry, capture, database
from codex_model_router.telemetry.central_protocol import validate_event, MAX_EVENT


class CentralClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.auth = None
        self.calls = []
        def secret(root, value=None):
            self.auth = self.auth or value
            return self.auth
        def send(path, body, token):
            self.calls.append((path, body))
            return {'accepted': [e['id'] for e in body.get('events', [])]}
        self.client = CentralTelemetry(self.root, secret=secret, send=send)
        self.start = patch.object(self.client, 'start')
        self.start.start()

    def tearDown(self):
        self.client.close()
        self.start.stop()
        self.temp.cleanup()

    def sample(self):
        capture(self.root, 'metrics', {'event': 'decision_accepted', 'thread': 'PRIVATE CHAT', 'decision_id': 'PRIVATE ID', 'model': 'gpt-6.1-sol', 'prompt': 'SECRET', 'title': 'SECRET'})

    def test_off_by_default_and_no_backfill(self):
        self.sample()
        self.assertFalse((self.root/'state/central-telemetry/outbox.sqlite3').exists())
        self.client.configure('enabled', True)
        self.assertEqual(self.client.snapshot()['pending'], 0)
        self.sample()
        self.client.tick()
        event = self.calls[-1][1]['events'][0]
        self.assertNotIn('PRIVATE', json.dumps(event))
        self.assertNotIn('SECRET', json.dumps(event))
        self.assertEqual(self.client.snapshot()['pending'], 0)
        count=len(self.calls)
        self.client.tick()
        self.assertEqual(len(self.calls),count)

    def test_diagnostics_need_independent_permission(self):
        self.client.configure('enabled', True)
        capture(self.root,'prompts',{'prompt':'synthetic','decision_id':'x'})
        capture(self.root,'raw_otlp',b'{"resourceLogs":[]}')
        self.assertEqual(self.client.snapshot()['pending'],0)
        self.client.configure('prompts',True)
        capture(self.root,'prompts',{'prompt':'synthetic','decision_id':'x'})
        capture(self.root,'raw_otlp',b'{"resourceLogs":[]}')
        self.assertEqual(self.client.snapshot()['pending'],1)
        self.client.configure('enabled',False)
        state=self.client.snapshot()
        self.assertFalse(state['prompts'])
        self.assertEqual(state['pending'],0)
        self.client.configure('enabled',True)
        self.assertFalse(self.client.snapshot()['prompts'])

    def test_retry_has_same_event_id_and_survives_new_client(self):
        self.client.configure('enabled',True)
        self.sample()
        original=self.client.send
        def failed(path,body,token):
            original(path,body,token)
            if path.endswith('events'):
                raise OSError('offline')
        self.client.send=failed
        with self.assertRaises(OSError): self.client.tick()
        event=self.calls[-1][1]['events'][0]
        with patch.object(CentralTelemetry, 'start'):
            recovered=CentralTelemetry(self.root,secret=self.client.secret,send=original)
        recovered.tick()
        self.assertEqual(self.calls[-1][1]['events'][0],event)
        self.assertEqual(self.client.snapshot()['pending'],0)

    def test_opt_out_during_enrollment_blocks_batch(self):
        self.client.configure('enabled',True)
        self.sample()
        send=self.client.send
        def disable(path,body,token):
            if path.endswith('enroll'): self.client.configure('enabled',False)
            return send(path,body,token)
        self.client.send=disable
        self.client.tick()
        self.assertFalse(any(path.endswith('events') for path,_ in self.calls))
        self.assertEqual(self.client.snapshot()['pending'],0)

    def test_capacity_is_counted_not_unbounded(self):
        self.client.configure('enabled',True)
        with patch('codex_model_router.telemetry.central_client.MAX_QUEUE_EVENTS',1):
            self.sample(); self.sample()
        self.assertEqual(self.client.snapshot()['pending'],1)
        self.assertEqual(self.client.snapshot()['rejected'],1)
        self.client.configure('raw_otlp',True)
        capture(self.root,'raw_otlp',json.dumps({'x':'x'*MAX_EVENT}))
        self.assertEqual(self.client.snapshot()['rejected'],2)

    def test_delete_waits_offline_and_clears_queue(self):
        self.client.configure('enabled',True)
        self.sample(); self.client.tick()
        self.sample(); self.client.configure('delete',True)
        self.assertEqual(self.client.snapshot()['pending'],0)
        self.assertTrue(self.client.snapshot()['delete_pending'])
        self.client.tick()
        self.assertEqual(self.calls[-1][0],'/v1/delete')
        self.assertEqual(self.client.snapshot()['status'],'deleted')

    def test_malformed_metrics_cannot_smuggle_text(self):
        valid={'id':'a'*32,'kind':'metrics','data':{'event':'decision_accepted'}}
        validate_event(valid)
        for key,value in [('prompt','secret'),('thread','original-id'),('model','arbitrary text'),('time',float('nan'))]:
            with self.assertRaises((ValueError,TypeError)):
                validate_event({**valid,'data':{**valid['data'],key:value}})

    def test_read_only_cannot_enable_or_spawn(self):
        client=CentralTelemetry(self.root,disabled=True)
        with self.assertRaises(ValueError): client.configure('enabled',True)
        self.assertIsNone(client.thread)

    def test_pause_is_acknowledged_without_repeating_network(self):
        self.client.configure('enabled',True)
        self.client.tick()
        self.client.configure('enabled',False)
        self.client.tick()
        count=len(self.calls)
        self.client.tick()
        self.assertEqual(len(self.calls),count)

    def test_real_journal_and_otlp_hooks_obey_permissions(self):
        from codex_model_router.storage.state_store import append_record, append_prompt_record
        from codex_model_router.telemetry.inference_telemetry import LocalInferenceTelemetry
        from urllib.request import Request, urlopen
        self.client.configure('enabled', True)
        self.client.configure('prompts', True)
        append_record(self.root/'state', {'event':'decision_created','decision_id':'synthetic'})
        append_prompt_record(self.root/'state', {'prompt':'synthetic prompt','decision_id':'synthetic'})
        collector=LocalInferenceTelemetry(lambda record: None, receive_raw=lambda raw:capture(self.root,'raw_otlp',raw))
        try:
            def submit():
                request=Request(collector.endpoint,data=b' {"resourceLogs": []} ',headers={'Authorization':'Bearer '+collector.token})
                with urlopen(request,timeout=3) as response:self.assertEqual(response.status,200)
            submit()
            self.assertEqual(self.client.snapshot()['pending'],2)
            self.client.configure('raw_otlp',True)
            submit()
            self.client.tick()
            event=self.calls[-1][1]['events'][0]
            self.assertEqual(event['kind'],'raw_otlp')
            self.assertEqual(event['data'],' {"resourceLogs": []} ')
            self.assertNotIn(collector.token,json.dumps(event))
        finally:
            collector.close()

    def test_monitor_actions_do_not_change_local_capture(self):
        from codex_model_router.monitor.monitor_state import MonitorState
        from codex_model_router.storage.state_store import atomic_json
        atomic_json(self.root/'config.local.json',{'enabled':True,'prompt_logging':False,'inference_telemetry':False})
        with patch.object(CentralTelemetry,'start'):
            monitor=MonitorState(self.root,code_root=Path(__file__).resolve().parents[1],platform='macos')
            try:
                monitor.action({'action':'config','key':'central_enabled','value':True})
                self.assertTrue(monitor.central.snapshot()['enabled'])
                local=json.loads((self.root/'config.local.json').read_text())
                self.assertFalse(local['prompt_logging'])
                self.assertFalse(local['inference_telemetry'])
            finally:monitor.close()

    def test_http_rejection_is_closed_and_never_exposes_response_content(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from codex_model_router.telemetry.central_client import transport
        body=BytesIO(b'PRIVATE_RESPONSE')
        error=HTTPError('https://router.andreifaur.dev/v1/events',507,'PRIVATE_MESSAGE',{},body)
        with patch('codex_model_router.telemetry.central_client.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaisesRegex(OSError,'^server_capacity$'):
                transport('/v1/events',{},'a'*64)
        self.assertTrue(body.closed)
