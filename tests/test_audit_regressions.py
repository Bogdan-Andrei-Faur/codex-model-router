"""End-to-end regressions from the general audit. No live provider or user state."""
import gzip
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.bridge.router import Router
from codex_model_router.routing.routing import DEFAULT_ROUTES, EFFORTS, select_route_details
from codex_model_router.routing.decision_engines import candidate_routes, jev_key, run_jev
from codex_model_router.telemetry.inference_telemetry import LocalInferenceTelemetry, MAX_DECODED_BYTES
from codex_model_router.bridge.request_dispatch import Dispatcher
from codex_model_router.storage.state_store import append_prompt_record, append_record, compact_history, compact_prompt_history, read_records
from codex_model_router.routing.workload import response_summary
from test_inference_telemetry import payload


def wire(value):
    return (json.dumps(value) + '\n').encode()


class AuditRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES, 'history_days': 0, 'routing_engine': 'jev'}))
        self.router = Router(self.config, self.root / 'state')
        self.resume(self.router)

    def resume(self, router):
        router.catalog = {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        router.client_line(wire({'id': 1, 'method': 'thread/resume', 'params': {'threadId': 'task-audit'}}))
        router.server_line(wire({'id': 1, 'result': {'thread': {'id': 'task-audit', 'name': 'Synthetic task'},
                                                   'model': 'gpt-6-luna', 'modelProvider': 'openai', 'reasoningEffort': 'low'}}))

    def request(self, text, request=2):
        return {'id': request, 'method': 'turn/start', 'params': {'threadId': 'task-audit', 'model': 'gpt-6-luna',
                                                                  'effort': 'low', 'input': [{'type': 'text', 'text': text}]}}

    def assistant(self, text):
        self.router.server_line(wire({'method': 'item/completed', 'params': {'threadId': 'task-audit',
            'item': {'type': 'agentMessage', 'text': text}}}))

    def test_resume_after_restart_keeps_strong_contract_past_neutral_and_weaker_updates(self):
        self.assistant('Queda pendiente corregir una vulnerabilidad de autenticación y validar las pruebas.')
        self.assistant('Falta investigar la integración y ejecutar pruebas.')
        self.assistant('He comprobado el primer archivo.')
        with (self.root / 'state' / 'history.jsonl').open('a') as stream:
            stream.write('{broken\n')
        self.router = Router(self.config, self.root / 'state')
        self.resume(self.router)
        with patch('codex_model_router.bridge.router.run_jev', return_value={'engine': 'jev', 'status': 'ok', 'route': {'model': 'gpt-6-luna', 'effort': 'low'}}):
            actual = json.loads(self.router.client_line(wire(self.request('Adelante'))))
        self.assertEqual(actual['params']['model'], 'gpt-6-astra')
        self.assertGreaterEqual(EFFORTS.index(actual['params']['effort']), EFFORTS.index('high'))

    def test_completion_and_thanks_do_not_inherit_technical_cost(self):
        for text in ('No queda nada pendiente.', 'Todo terminado, sin riesgo ni trabajo pendiente.'):
            with self.subTest(text=text):
                summary = response_summary(text)
                self.assertTrue(summary['completed'])
                route, _ = select_route_details('Gracias', DEFAULT_ROUTES, 'critical', 'max', response_context=summary)
                self.assertEqual(route, {'model': 'gpt-6-luna', 'effort': 'low'})
        self.assistant('Queda pendiente corregir seguridad.')
        self.assistant('No queda nada pendiente.')
        restarted = Router(self.config, self.root / 'state')
        self.assertEqual(restarted.thread_categories['task-audit']['task_contract']['status'], 'completed')

    def test_independent_change_allows_jev_terra_but_keeps_pending_contract(self):
        self.assistant('Queda pendiente corregir una vulnerabilidad de autenticación y validar las pruebas.')
        self.router = Router(self.config, self.root / 'state')
        self.resume(self.router)
        with patch('codex_model_router.bridge.router.run_jev', return_value={'engine': 'jev', 'status': 'ok',
                   'route': {'model': 'gpt-6.1-sol', 'effort': 'medium'}}) as jev:
            actual = json.loads(self.router.client_line(wire(self.request('Ok, implementa un formulario de contactos'))))
        self.assertEqual(actual['params']['model'], 'gpt-6.1-sol')
        state = jev.call_args.args[2]
        self.assertNotIn('previous_response_context', state)
        self.assertEqual(state['quality_floor'], 'normal')
        self.assertEqual(self.router.threads['task-audit']['task_contract']['floor'], 'critical')
        self.router.server_line(wire({'id': 2, 'result': {'turn': {'id': 'turn-independent'}}}))
        self.router.server_line(wire({'method': 'turn/completed', 'params': {
            'threadId': 'task-audit', 'turn': {'id': 'turn-independent', 'status': 'completed'}}}))
        followup = self.request('Sigue con lo que falta', 3)
        followup['params'].update(model='gpt-6.1-sol', effort='medium')
        with patch('codex_model_router.bridge.router.run_jev', return_value={'engine': 'jev', 'status': 'ok',
                   'route': {'model': 'gpt-6.1-sol', 'effort': 'medium'}}):
            actual = json.loads(self.router.client_line(wire(followup)))
        self.assertEqual(actual['params']['model'], 'gpt-6-astra')

    def test_progress_completion_does_not_close_whole_task(self):
        self.assistant('Queda pendiente corregir una vulnerabilidad y validar pruebas.')
        self.router.server_line(wire({'method':'item/completed','params':{'threadId':'task-audit',
            'item':{'type':'agentMessage','phase':'commentary','text':'Todo terminado.'}}}))
        self.assertEqual(self.router.threads['task-audit']['task_contract']['status'], 'pending')
        self.assertEqual(self.router.threads['task-audit']['task_contract']['floor'], 'critical')

    def test_broad_validation_minimum_applies_to_provider_effort_too(self):
        _, policy = select_route_details('Haz todas las pruebas y validaciones necesarias; entorno local con base de datos de prueba', DEFAULT_ROUTES)
        choices = candidate_routes(DEFAULT_ROUTES, self.router.catalog, policy)
        self.assertTrue(choices)
        self.assertTrue(all(EFFORTS.index(r['effort']) >= EFFORTS.index('high') for r in choices.values()))

    def test_malformed_provider_uses_local_fallback_and_records_decision(self):
        for response in ([], {'answers': []}, {'answers': {'route': []}}, None, 'wrong'):
            with self.subTest(response=response), patch('codex_model_router.routing.decision_engines.jev_key', return_value='synthetic'), patch('codex_model_router.routing.decision_engines._post_json', return_value=response):
                self.router.pending.clear()
                actual = json.loads(self.router.client_line(wire(self.request('Haz una auditoría exhaustiva de seguridad'))))
                self.assertEqual(actual['params']['model'], 'gpt-6-astra')
                self.assertTrue(self.router.current_decisions.get('task-audit'))
        self.assertTrue(any(r.get('event') == 'decision_routed' for r in read_records(self.root / 'state/history.jsonl')))

    def test_new_decision_clears_inference_evidence_and_binds_build(self):
        row = self.router.threads['task-audit']
        row.update(observed_model='gpt-6-astra', observed_effort='max', inference_source='old', tokens={'inputTokens': 1}, turn_id='old')
        self.router.new_decision('task-audit', 'gpt-6-luna', 'low', 'synthetic', 'synthetic', 'automatic')
        for key in ('observed_model', 'observed_effort', 'tokens', 'inference_source', 'turn_id'):
            self.assertNotIn(key, row)
        record = list(read_records(self.root / 'state/history.jsonl'))[-1]
        self.assertTrue(record['build_id'])
        self.assertEqual(record['routing_policy_version'], 8)

    def test_identical_routed_wire_is_still_one_automatic_decision(self):
        self.config.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES}))
        request = self.request('Traduce hola')
        raw = (json.dumps(request, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
        self.assertEqual(self.router.client_line(raw), raw)
        created = [r for r in read_records(self.root / 'state/history.jsonl') if r['event']=='decision_created']
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]['source'], 'automatic')

    def test_disk_failure_does_not_restore_the_small_original_model(self):
        with patch('codex_model_router.bridge.router.persist_task', side_effect=OSError('synthetic')), patch('codex_model_router.bridge.router.run_jev', return_value={'engine':'jev', 'status':'unavailable'}):
            result = json.loads(self.router.client_line(wire(self.request('Audita toda la autenticación'))))
        self.assertEqual(result['params']['model'], 'gpt-6-astra')

    def test_new_task_clear_survives_another_restart(self):
        self.assistant('Queda pendiente corregir autenticación.')
        self.router = Router(self.config, self.root / 'state'); self.resume(self.router)
        with patch('codex_model_router.bridge.router.run_jev', return_value={'engine':'jev','status':'unavailable'}):
            self.router.client_line(wire(self.request('Nueva tarea: traduce hola')))
        restored = Router(self.config, self.root / 'state').thread_categories['task-audit']
        self.assertNotIn('task_floor', restored)
        self.assertNotIn('task_contract', restored)

    def test_delayed_and_duplicate_inferences_never_confirm_new_turn(self):
        row = self.router.threads['task-audit']
        row.update(phase_status='active', phase_model='gpt-6-luna', phase_effort='low', turn_id='turn-current', decision_started_at=time.time())
        self.router.current_decisions['task-audit'] = 'decision-current'
        base = dict(event_kind='response.completed', model='gpt-6-luna', effort='low', thread_id='task-audit')
        self.router.observe_inference(dict(base, turn_id='turn-old', event_id='old'))
        self.assertNotIn('observed_model', row)
        record = dict(base, turn_id='turn-current', event_id='new', timestamp=time.time())
        self.router.observe_inference(record)
        self.router.observe_inference(record)
        self.assertEqual(self.router.stats['telemetry_confirmed'], 1)

    def test_provider_wait_releases_router_and_cancel_never_forwards_turn(self):
        entered, release = threading.Event(), threading.Event()
        def slow(*args):
            entered.set(); release.wait(2)
            return {'engine': 'jev', 'status': 'unavailable'}
        native, client = [], []
        dispatcher = Dispatcher(self.router, native.append, client.append)
        self.addCleanup(dispatcher.close)
        with patch('codex_model_router.bridge.router.run_jev', side_effect=slow):
            dispatcher.submit(wire(self.request('Audita exhaustivamente la seguridad')))
            self.assertTrue(entered.wait(1))
            self.assertTrue(self.router.lock.acquire(timeout=.2))
            self.router.lock.release()
            started = time.monotonic()
            dispatcher.submit(wire({'id': 3, 'method': 'turn/interrupt', 'params': {'threadId': 'task-audit'}}))
            self.assertLess(time.monotonic() - started, .2)
            release.set(); dispatcher.queue.join()
        self.assertEqual(native, [])
        self.assertEqual(len(client), 2)
        self.assertNotIn('task-audit', self.router.pending)

    def test_invalid_thread_id_is_forwarded_to_native_validation(self):
        native = []
        dispatcher = Dispatcher(self.router, native.append, lambda value: None)
        self.addCleanup(dispatcher.close)
        message = wire({'id': 99, 'method': 'turn/start', 'params': {'threadId': []}})
        dispatcher.submit(message)
        self.assertEqual(native, [message])

    def test_classifier_total_deadline_includes_credentials(self):
        done, entered, finished = threading.Event(), threading.Event(), threading.Event()
        def slow(*args):
            entered.set()
            done.wait(5)
            return None
        results = []
        def classify():
            try:
                results.append(run_jev({'jev': {'timeout_seconds': .1}}, self.root, {}, {}))
            finally:
                finished.set()
        with patch('codex_model_router.routing.decision_engines.jev_key', side_effect=slow):
            worker = threading.Thread(target=classify, daemon=True)
            worker.start()
            try:
                self.assertTrue(entered.wait(2), 'Credential lookup did not start')
                # Prove timeout returns while credentials remain blocked;
                # scheduler delays and circuit-state writes are not a deadline.
                self.assertTrue(finished.wait(2), 'Deadline waited for credential lookup')
                self.assertFalse(done.is_set())
                self.assertEqual(results[0]['engine_failure'], 'timeout')
            finally:
                done.set()
                worker.join(timeout=2)

    def test_forever_history_and_concurrent_process_writers(self):
        state = self.root / 'journal'; state.mkdir()
        history = state / 'history.jsonl'
        history.write_text(''.join(json.dumps({'event': 'old', 'time': 1, 'index': i})+'\n' for i in range(20005)))
        compact_history(state, 0)
        self.assertEqual(len(list(read_records(history))), 20005)
        code = 'import sys; sys.path.insert(0, ' + repr(str(Path(__file__).resolve().parents[1] / 'src')) + '); from codex_model_router.storage.state_store import append_record; import sys; from pathlib import Path; [append_record(Path(sys.argv[1]), {"event":"parallel", "writer":sys.argv[2], "i":i}) for i in range(40)]'
        processes = [subprocess.Popen([sys.executable, '-c', code, str(state), str(n)], cwd=Path(__file__).resolve().parents[1]) for n in range(3)]
        for process in processes:
            self.assertEqual(process.wait(timeout=10), 0)
        values = [r for r in read_records(history) if r['event'] == 'parallel']
        self.assertEqual(len({(r['writer'], r['i']) for r in values}), 120)

    def test_prompt_history_uses_the_configured_retention_window(self):
        state = self.root / 'prompt-journal'
        now = 200 * 86400
        append_prompt_record(state, {'time': now - 91 * 86400, 'prompt': 'old'})
        append_prompt_record(state, {'time': now - 89 * 86400, 'prompt': 'recent'})
        compact_prompt_history(state, 90, now=now)
        self.assertEqual(list(read_records(state / 'prompts.jsonl')),
                         [{'time': now - 89 * 86400, 'prompt': 'recent'}])

    def test_credentials_are_bound_to_connection_and_legacy_is_not_reused(self):
        (self.root / 'jev.secret').write_bytes(b'legacy')
        (self.root / 'jev-typesafe.secret').write_bytes(b'typesafe')
        with patch('codex_model_router.routing.decision_engines.sys.platform', 'win32'), patch.dict(os.environ, {'PERSONAL_CODEX_JEV_API_KEY': 'unbound'}, clear=True), patch('codex_model_router.routing.decision_engines._unprotect_windows', side_effect=lambda x:x.decode()):
            self.assertEqual(jev_key(self.root, 'typesafe'), 'typesafe')
            self.assertIsNone(jev_key(self.root, 'vercel'))
        with patch.dict(os.environ, {'AI_GATEWAY_API_KEY': 'vercel'}, clear=True):
            self.assertEqual(jev_key(self.root, 'vercel'), 'vercel')
        with patch.dict(os.environ, {}, clear=True), patch('codex_model_router.routing.decision_engines.sys.platform', 'darwin'), patch('codex_model_router.routing.decision_engines._keychain_key', side_effect=lambda state, key: key):
            self.assertEqual(jev_key(self.root, 'vercel'), 'jev-vercel')
            self.assertEqual(jev_key(self.root, 'typesafe'), 'jev-typesafe')


class CollectorBoundaryTests(unittest.TestCase):
    def test_fast_unauthorized_requests_do_not_leave_timer_threads(self):
        collector = LocalInferenceTelemetry(lambda x: None)
        self.addCleanup(collector.close)
        before = len(threading.enumerate())
        for _ in range(50):
            try:
                urlopen(Request(collector.endpoint, data=b'{}'), timeout=3)
                self.fail('unauthorized request accepted')
            except HTTPError as error:
                self.assertEqual(error.code, 401)
                error.close()
        time.sleep(.05)
        self.assertLessEqual(len(threading.enumerate()), before + 2)

    def test_authentication_and_expansion_budget(self):
        events = []
        collector = LocalInferenceTelemetry(events.append)
        self.addCleanup(collector.close)
        raw = json.dumps(payload()).encode()
        for token, body, encoding, code in [('', raw, None, 401), ('wrong', raw, None, 401),
            (collector.token, gzip.compress(b' '*(MAX_DECODED_BYTES+1)), 'gzip', 413),
            (collector.token, gzip.compress(b' '*MAX_DECODED_BYTES)+gzip.compress(b' '), 'gzip', 413),
            (collector.token, gzip.compress(raw)[:-7], 'gzip', 400),
            (collector.token, b'[]', None, 400)]:
            headers = {'Authorization': 'Bearer '+token}
            if encoding: headers['Content-Encoding'] = encoding
            with self.subTest(code=code), self.assertRaises(HTTPError) as error:
                urlopen(Request(collector.endpoint, data=body, headers=headers), timeout=3)
            self.assertEqual(error.exception.code, code)
            error.exception.close()
        self.assertEqual(events, [])
        with urlopen(Request(collector.endpoint, data=raw, headers={'Authorization': 'Bearer '+collector.token}), timeout=3) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(len(events), 1)
        self.assertNotIn(collector.token, json.dumps(collector.snapshot()))

    def test_slow_connections_are_bounded_and_receiver_recovers(self):
        collector = LocalInferenceTelemetry(lambda x: None)
        self.addCleanup(collector.close)
        sockets = []
        try:
            for _ in range(10):
                sock = socket.create_connection(('127.0.0.1', collector.server.server_port), timeout=1)
                sock.sendall(b'POST /v1/logs HTTP/1.0\r\n'); sockets.append(sock)
            time.sleep(2.2)
            with urlopen(Request(collector.endpoint, data=json.dumps(payload()).encode(), headers={'Authorization': 'Bearer '+collector.token}), timeout=3) as response:
                self.assertEqual(response.status, 200)
        finally:
            for sock in sockets: sock.close()


if __name__ == '__main__': unittest.main()
