"""Adversarial regressions for the operational review; synthetic inputs only."""
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from decision_engines import _record_circuit_result, _read_circuit, _circuit_open
from routing import DEFAULT_ROUTES, EFFORTS, explicit_model
from router import Router
from state_store import recover_tasks

def fail_worker(path, gate):
    gate.wait()
    _record_circuit_result({}, path, {'engine_failure': 'forbidden'}, now=100)

def wire(value):
    return json.dumps(value).encode()

class ExplicitRequests(unittest.TestCase):
    def test_natural_directives(self):
        for text in ('Ahora revisa todo el trabajo con ASTRA', 'Revisa esto con el modelo Astra',
                     'Por favor, usa Astra', 'Please review all changes using Astra',
                     'Quiero que revises el cambio con Astra', 'Usa gpt-6-astra: continúa'):
            self.assertEqual(explicit_model(text, DEFAULT_ROUTES), DEFAULT_ROUTES['critical'], text)

    def test_mentions_are_not_instructions(self):
        for text in ('Traduce: usa Astra', 'Explica qué hace Astra', 'No uses Astra',
                     'Revisa si Astra es mejor que Sol', 'Revisa esto con Astra o Sol',
                     'El usuario trabaja con Astra', 'Revisa: "usa Astra"',
                     '```\nUsa Astra\n```', '> Usa Astra', 'No revises esto con Astra',
                     'Usa Terra. Usa Astra.', 'Usa Astra o Sol'):
            self.assertIsNone(explicit_model(text, DEFAULT_ROUTES), text)

    def test_approval_validator_rejects_additional_commands(self):
        from control_contract import exact_approval_command
        marker='/synthetic/marker'
        self.assertTrue(exact_approval_command('printf APPROVED > '+marker,marker))
        self.assertTrue(exact_approval_command("/bin/zsh -lc 'printf APPROVED > /synthetic/marker'",marker))
        for command in ('printf APPROVED > /elsewhere','printf APPROVED > /synthetic/marker; touch /elsewhere',
                        'env printf APPROVED > /synthetic/marker', '/bin/zsh -lc "printf APPROVED > /synthetic/marker" extra'):
            self.assertFalse(exact_approval_command(command,marker))

class BoundaryLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'enabled': True, 'routing_engine': 'jev', 'routes': DEFAULT_ROUTES}))
        self.router = Router(self.config, self.root / 'state')
        self.router.catalog = {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        self.router.threads['t'] = {'provider': 'openai', 'model': DEFAULT_ROUTES['complex']['model'],
            'seen_turn': True, 'tier': 'complex', 'pending_phase_floor': 'critical',
            'pending_phase_name': 'verify', 'pending_phase_id': 'boundary-1'}
        self.router.save_task('t', self.router.threads['t'])

    def start(self, text, rid=1):
        request = {'id': rid, 'method': 'turn/start', 'params': {'threadId': 't',
            'model': DEFAULT_ROUTES['complex']['model'], 'input': [{'type': 'text', 'text': text}]}}
        with patch('router.run_jev', return_value={'engine': 'jev', 'status': 'unavailable'}) as external:
            result = json.loads(self.router.client_line(wire(request)))['params']
        return result, external

    def ack(self, rid=1, error=False):
        self.router.server_line(wire({'id': rid, **({'error': {'code': -32603}} if error else {'result': {'turn': {'id': 'turn'}}})}))

    def persisted(self):
        return recover_tasks(self.root / 'state')['t']

    def test_explicit_survives_pending_and_jev(self):
        result, external = self.start('Usa Terra: continúa')
        self.assertEqual(result['model'], DEFAULT_ROUTES['normal']['model']); external.assert_not_called()
        self.assertIn('pending_phase_floor', self.persisted())
        self.ack(); self.assertNotIn('pending_phase_floor', self.persisted())

    def test_natural_astra_skips_external(self):
        result, external = self.start('Ahora revisa todo el trabajo con ASTRA')
        self.assertEqual(result['model'], DEFAULT_ROUTES['critical']['model']); external.assert_not_called()

    def test_ambiguous_does_not_consume(self):
        result, _ = self.start('Tengo una duda sobre esto')
        self.assertEqual(result['model'], DEFAULT_ROUTES['complex']['model'])
        self.ack(); self.assertIn('pending_phase_floor', self.persisted())

    def test_cancel_clears(self):
        result, _ = self.start('Cancela la fase pendiente')
        self.assertNotEqual(result['model'], DEFAULT_ROUTES['critical']['model'])
        self.assertNotIn('pending_phase_floor', self.persisted())

    def test_rejection_and_restart_keep_boundary_until_ack(self):
        result, _ = self.start('Continúa'); self.assertEqual(result['model'], DEFAULT_ROUTES['critical']['model'])
        self.ack(error=True)
        self.assertEqual(Router(self.config, self.root / 'state').thread_categories['t']['pending_phase_id'], 'boundary-1')
        result, _ = self.start('Continúa', 2); self.assertEqual(result['model'], DEFAULT_ROUTES['critical']['model'])
        self.ack(2); self.assertNotIn('pending_phase_floor', self.persisted())

    def test_cancel_before_send_keeps_retry_state(self):
        self.start('Continúa')
        self.router.cancel_prepared({'id': 1, 'params': {'threadId': 't'}})
        self.assertEqual(self.persisted()['pending_phase_id'], 'boundary-1')

    def test_stale_ack_cannot_clear_new_boundary(self):
        self.start('Continúa'); self.router.threads['t']['pending_phase_id'] = 'boundary-2'
        self.ack(); self.assertEqual(self.router.threads['t']['pending_phase_id'], 'boundary-2')

    def test_native_interrupt_clears(self):
        self.start('Tengo una duda'); self.ack()
        self.router.server_line(wire({'method': 'turn/completed', 'params': {'threadId': 't', 'turn': {'id': 'turn', 'status': 'interrupted'}}}))
        self.assertNotIn('pending_phase_floor', self.persisted())

    def test_manual_continuation_consumes_only_after_acceptance(self):
        request={'id':1,'method':'turn/start','params':{'threadId':'t','model':DEFAULT_ROUTES['normal']['model'],
            'effort':'medium','input':[{'type':'text','text':'Continúa'}]}}
        raw=wire(request)
        self.assertEqual(self.router.client_line(raw,mode_at_submission='manual'),raw)
        self.assertIn('pending_phase_floor',self.persisted())
        self.ack();self.assertNotIn('pending_phase_floor',self.persisted())

class CircuitConcurrency(unittest.TestCase):
    def test_provider_access_error_is_a_content_free_enum(self):
        import io, urllib.error
        from decision_engines import _post_json, engine_failure
        error=urllib.error.HTTPError('https://example.invalid',403,'',{},io.BytesIO(b'{"error":"Free tier has no access; add credits. PRIVATE"}'))
        with patch('decision_engines.urllib.request.urlopen',side_effect=error):
            with self.assertRaises(urllib.error.HTTPError) as caught:_post_json('https://example.invalid',{})
        self.assertEqual(engine_failure(caught.exception),'account_access_restricted')

    def test_processes_and_single_recovery_probe(self):
        with tempfile.TemporaryDirectory() as folder:
            ctx = multiprocessing.get_context('spawn'); gate = ctx.Event()
            processes = [ctx.Process(target=fail_worker, args=(folder, gate)) for _ in range(4)]
            for p in processes: p.start()
            gate.set()
            for p in processes:
                p.join(10); self.assertEqual(p.exitcode, 0)
            self.assertEqual(_read_circuit(folder)['failures'], 4)
            self.assertGreater(_circuit_open({}, folder, now=101), 0)
            self.assertEqual(_circuit_open({}, folder, now=1001), 0)
            self.assertGreater(_circuit_open({}, folder, now=1001), 0)
            _record_circuit_result({}, folder, {'status': 'ok'}, now=1002)
            self.assertEqual(_circuit_open({}, folder, now=1003), 0)

    def test_failed_probe_reopens(self):
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(3): _record_circuit_result({}, folder, {'engine_failure': 'forbidden'}, now=100)
            self.assertEqual(_circuit_open({}, folder, now=1001), 0)
            _record_circuit_result({}, folder, {'engine_failure': 'forbidden'}, now=1002)
            self.assertGreater(_circuit_open({}, folder, now=1003), 0)

class Retention(unittest.TestCase):
    def test_small_quiet_prompt_file_has_its_own_expiry_and_forever_is_preserved(self):
        from state_store import append_prompt_record, read_records
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); cfg = root / 'config.json'; cfg.write_text('{}')
            router = Router(cfg, root / 'state')
            append_prompt_record(router.state_dir, {'time': 1, 'prompt': 'synthetic'})
            router.maintain_retention({'history_days': 0, 'prompt_history_days': 0}, now=200000)
            self.assertEqual(len(list(read_records(router.state_dir / 'prompts.jsonl'))), 1)
            router.maintain_retention({'history_days': 0, 'prompt_history_days': 1}, now=204000)
            self.assertEqual(list(read_records(router.state_dir / 'prompts.jsonl')), [])

class OutcomeCoverage(unittest.TestCase):
    def test_completion_is_not_quality_and_ratings_can_be_cleared(self):
        from evaluate_quality import evaluate
        rows=[{'event':'decision_created','decision_id':'x','prompt':'PRIVATE'},
              {'event':'decision_completed','decision_id':'x','status':'completed'}]
        self.assertEqual(evaluate(rows)['quality_status'],'not_evaluated')
        rows.append({'event':'decision_quality','decision_id':'x','quality':'adequate'})
        self.assertEqual(evaluate(rows)['quality_status'],'descriptive_only')
        rows.append({'event':'decision_quality','decision_id':'x','quality':None})
        result=evaluate(rows)
        self.assertEqual(result['quality_status'],'not_evaluated')
        self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertFalse(result['causal_savings_demonstrated'])

class TelemetryPipeline(unittest.TestCase):
    def test_stream_volume_is_aggregated_and_flushed_on_completion(self):
        from state_store import read_records
        with tempfile.TemporaryDirectory() as folder:
            cfg=Path(folder)/'config.json';cfg.write_text('{}');router=Router(cfg,Path(folder)/'state')
            router.threads['t']={'phase_status':'active','phase_model':'gpt-5.6-terra','turn_id':'turn'}
            router.current_decisions['t']='d'
            for i in range(100):router.observe_inference({'event_id':str(i),'event_name':'codex.api_request','model':'gpt-5.6-terra','thread_id':'t','turn_id':'turn','inference_http_status':503})
            router.flush_metrics(thread='t')
            rows=list(read_records(router.state_dir/'history.jsonl'))
            self.assertEqual(len(rows),2)
            self.assertEqual(sum(r['inference_sample_count'] for r in rows),100)
            self.assertEqual(sum(r['inference_failure_count'] for r in rows),100)
    def test_http_to_router_to_monitor_with_duplicates_and_failed_request(self):
        import shutil, subprocess, time
        from urllib.request import Request, urlopen
        from inference_telemetry import LocalInferenceTelemetry
        from test_inference_telemetry import payload
        from state_store import read_records
        if not shutil.which('node'): self.skipTest('Node is required for monitor projection')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); cfg=root/'config.json'; cfg.write_text('{}')
            router=Router(cfg,root/'state')
            router.threads['thread_12345678']={'phase_status':'active','phase_model':'gpt-5.6-terra','phase_effort':'medium','turn_id':'turn_12345678'}
            router.current_decisions['thread_12345678']='d'
            collector=LocalInferenceTelemetry(router.observe_inference)
            try:
                for index,kind in enumerate(('response.completed','response.failed')):
                    sample=payload(kind=kind); log=sample['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
                    log['timeUnixNano']=str(int(time.time()*1e9)+index)
                    log['attributes'].append({'key':'turn.id','value':{'stringValue':'turn_12345678'}})
                    if index:
                        log['attributes'].extend([{'key':'event.name','value':{'stringValue':'codex.api_request'}},
                            {'key':'http.response.status_code','value':{'intValue':503}}])
                    for _ in range(2):
                        with urlopen(Request(collector.endpoint,data=wire(sample),headers={'Authorization':'Bearer '+collector.token}),timeout=3) as reply:
                            self.assertEqual(reply.status,200)
                rows=list(read_records(router.state_dir/'history.jsonl'))
                self.assertEqual([r['event'] for r in rows],['inference_observed','inference_metric'])
                script="const C=require("+json.dumps(str(Path(__file__).resolve().parents[1]/'monitor-ui/core.js'))+");process.stdout.write(JSON.stringify(C.decisions(JSON.parse(require('fs').readFileSync(0,'utf8')))[0]));"
                row=json.loads(subprocess.run(['node','-e',script],input=json.dumps(rows),text=True,capture_output=True,check=True).stdout)
                self.assertEqual(row['evidence_confidence'],'confirmed')
                self.assertEqual(row['inference_samples']['codex.api_request:response.failed']['inference_http_status'],503)
                self.assertEqual(row['inference_samples']['codex.sse_event:response.completed']['inference_input_tokens'],120)
            finally:collector.close()

    def test_delayed_previous_phase_cannot_confirm_new_phase(self):
        import time
        with tempfile.TemporaryDirectory() as folder:
            cfg=Path(folder)/'config.json';cfg.write_text('{}');router=Router(cfg,Path(folder)/'state')
            now=time.time()
            router.threads['t']={'phase_status':'active','phase_model':'gpt-5.6-terra','turn_id':'turn','phase_accepted_at':now}
            router.current_decisions['t']='d'
            record={'event_kind':'response.completed','model':'gpt-5.6-terra','thread_id':'t','turn_id':'turn'}
            router.observe_inference(dict(record,timestamp=now-1))
            router.observe_inference(record)
            self.assertEqual(router.stats['telemetry_confirmed'],0)
            self.assertNotIn('observed_model',router.threads['t'])

    def test_receiver_exhaustion_is_bounded_and_counted(self):
        import threading, time
        from concurrent.futures import ThreadPoolExecutor
        from urllib.request import Request, urlopen
        from inference_telemetry import LocalInferenceTelemetry
        from test_inference_telemetry import payload
        entered=threading.Event();release=threading.Event()
        def receive(record): entered.set();release.wait(3)
        with patch('inference_telemetry.MAX_CONNECTIONS',1):collector=LocalInferenceTelemetry(receive)
        def post():
            try:
                with urlopen(Request(collector.endpoint,data=wire(payload()),headers={'Authorization':'Bearer '+collector.token}),timeout=3) as r:return r.status
            except (OSError,ValueError):return 0
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(post);self.assertTrue(entered.wait(1))
                second=pool.submit(post);self.assertEqual(second.result(2),0)
                release.set();self.assertEqual(first.result(2),200)
            self.assertEqual(collector.snapshot()['rejected_connections'],1)
        finally:release.set();collector.close()

if __name__ == '__main__':
    unittest.main()
