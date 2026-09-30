"""Review calibration and native failure lifecycle; all events are synthetic."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from error_diagnostics import native_error, rpc_error, ERROR_TYPES, HTTP_ERRORS
from router import Router
from routing import DEFAULT_ROUTES, EFFORTS, classify, select_route_details
from decision_engines import candidate_routes
from state_store import read_records


def wire(value):
    return (json.dumps(value) + '\n').encode()


class ReviewPolicyTests(unittest.TestCase):
    def test_open_reviews_require_sol_high_even_when_short(self):
        for text in ('Haz una revision de como esta iendo', 'Haz una revisión de cómo está yendo',
                     'Ok, revisa cómo va el proyecto', 'Revisa el repositorio y dime qué falta',
                     'Puedes revisar el enrutador', 'Please review how things are going',
                     'Could you review the current state of the project?', 'Review project progress'):
            with self.subTest(text=text):
                decision = classify(text)
                self.assertEqual((decision.quality_floor, decision.effort, decision.request_kind),
                                 ('complex', 'high', 'project_review'))
                _, policy = select_route_details(text, DEFAULT_ROUTES)
                choices = candidate_routes(DEFAULT_ROUTES, {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}, policy)
                self.assertTrue(choices)
                self.assertTrue(all(r['tier'] not in ('simple', 'normal') and
                                    EFFORTS.index(r['effort']) >= EFFORTS.index('high') for r in choices.values()))

    def test_bounded_and_non_directive_requests_do_not_gain_review_floor(self):
        for text in ('Traduce: revisa cómo va el proyecto', 'Revisa solo la ortografía de esta frase del proyecto',
                     'Revisa solo el color del icono del router', 'Check receiver status',
                     'Dime los contadores de la telemetría', '¿Cómo va?',
                     'Qué significa revisión del proyecto', 'No revises el proyecto',
                     'Explica esta frase:\n> Revisa el proyecto'):
            with self.subTest(text=text):
                self.assertNotEqual(classify(text).request_kind, 'project_review')

    def test_independent_review_does_not_inherit_critical_work(self):
        context = {'implementation_pending': True, 'work_floor': 'critical'}
        self.assertEqual(classify('Haz una revision de como esta iendo', 'critical', response_context=context).quality_floor, 'complex')
        self.assertEqual(classify('Sigue revisando el proyecto', 'critical', response_context=context).quality_floor, 'critical')
        self.assertEqual(classify('Dale', 'critical', response_context=context).quality_floor, 'critical')
        self.assertIsNone(classify('Dale formato a este texto', 'critical', response_context=context).quality_floor)
        self.assertEqual(classify('Revisa la autenticación del proyecto').quality_floor, 'complex')
        self.assertEqual(classify('Audita una vulnerabilidad del proyecto').quality_floor, 'critical')
        route, policy = select_route_details('Usa Luna: revisa el proyecto', DEFAULT_ROUTES)
        self.assertEqual((route['model'], policy['source']), ('gpt-6-luna', 'explicit'))


class DiagnosticSanitizerTests(unittest.TestCase):
    def test_all_known_native_categories(self):
        for kind in ERROR_TYPES:
            self.assertEqual(native_error({'codexErrorInfo': kind, 'message': 'PRIVATE'})['error_type'], kind)
        for kind in HTTP_ERRORS:
            self.assertEqual(native_error({'codexErrorInfo': {kind: {'httpStatusCode': 503}}}),
                             {'error_type': kind, 'error_http_status': 503, 'error_source': 'native'})
        self.assertEqual(native_error({'codexErrorInfo': {'activeTurnNotSteerable': {'turnKind': 'review'}}})['error_type'], 'activeTurnNotSteerable')

    def test_no_free_text_or_malformed_http_codes_are_retained(self):
        for info in ('PRIVATE', ['PRIVATE'], {'PRIVATE': {}}, {'other': {}, 'PRIVATE': {}}, None):
            self.assertEqual(native_error({'message': 'PRIVATE', 'codexErrorInfo': info,
                             'additionalDetails': 'PRIVATE', 'misalignment': {'steer': {'message': 'PRIVATE'}}}),
                             {'error_type': 'unknown', 'error_source': 'native'})
        for status in ('PRIVATE', True, 0, 99, 600, 503.0, None, {}):
            result = native_error({'codexErrorInfo': {'httpConnectionFailed': {'httpStatusCode': status}}})
            self.assertNotIn('error_http_status', result)
        for value in ([], 'PRIVATE', None):
            self.assertEqual(native_error(value)['error_type'], 'unknown')

    def test_rpc_codes_are_bounded_integers(self):
        self.assertEqual(rpc_error({'code': -32603, 'message': 'PRIVATE'})['error_code'], -32603)
        for value in ('PRIVATE', True, 2**64, None, []):
            self.assertNotIn('error_code', rpc_error({'code': value}))


class NativeLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        config = self.root / 'config.json'
        config.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES}))
        self.router = Router(config, self.root / 'state')
        self.router.catalog = {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        self.router.client_line(wire({'id': 1, 'method': 'thread/resume', 'params': {'threadId': 'task'}}))
        self.router.server_line(wire({'id': 1, 'result': {'thread': {'id': 'task', 'name': 'Synthetic'},
                                                     'modelProvider': 'openai', 'model': 'gpt-6-luna', 'reasoningEffort': 'low'}}))
        self.begin()

    def begin(self, turn='turn-1', request=2):
        self.router.client_line(wire({'id': request, 'method': 'turn/start', 'params': {'threadId': 'task',
            'model': 'gpt-6-luna', 'effort': 'low', 'input': [{'type': 'text', 'text': 'Traduce hola'}]}}))
        self.router.server_line(wire({'id': request, 'result': {'turn': {'id': turn}}}))

    def notify(self, retry=False, turn='turn-1', error=None):
        event = wire({'method': 'error', 'params': {'threadId': 'task', 'turnId': turn, 'willRetry': retry,
            'error': error or {'message': 'PRIVATE', 'additionalDetails': 'PRIVATE',
                              'codexErrorInfo': {'responseStreamDisconnected': {'httpStatusCode': 502}}}}})
        self.assertIs(self.router.server_line(event), True)

    def complete(self, status='failed', error=None, turn='turn-1'):
        event = wire({'method': 'turn/completed', 'params': {'threadId': 'task',
                      'turn': {'id': turn, 'status': status, 'error': error}}})
        self.assertIs(self.router.server_line(event), True)

    def records(self, event):
        return [r for r in read_records(self.root / 'state/history.jsonl') if r['event'] == event]

    def test_failed_turn_retains_only_native_category_and_http_status(self):
        self.complete(error={'message': 'PRIVATE', 'additionalDetails': 'PRIVATE',
                             'codexErrorInfo': {'httpConnectionFailed': {'httpStatusCode': 503}}})
        row = self.router.threads['task']
        self.assertEqual((row['error_type'], row['error_http_status']), ('httpConnectionFailed', 503))
        self.assertEqual(self.records('decision_completed')[-1]['error_type'], 'httpConnectionFailed')
        for path in (self.root / 'state').glob('*.json*'):
            self.assertNotIn('PRIVATE', path.read_text())

    def test_terminal_notification_fills_missing_completion_cause(self):
        self.notify()
        self.complete()
        self.assertEqual(self.records('decision_completed')[-1]['error_http_status'], 502)
        self.assertFalse(self.router.native_errors)

    def test_completion_cause_takes_precedence(self):
        self.notify()
        self.complete(error={'codexErrorInfo': 'usageLimitExceeded'})
        result = self.records('decision_completed')[-1]
        self.assertEqual(result['error_type'], 'usageLimitExceeded')
        self.assertNotIn('error_http_status', result)

    def test_retry_does_not_finish_or_fail_a_successful_turn(self):
        self.notify(retry=True)
        self.assertNotIn('error_type', self.router.threads['task'])
        self.assertNotIn('completed_at', self.router.threads['task'])
        self.assertFalse(self.records('decision_error'))
        self.assertFalse(self.records('decision_completed'))
        self.complete('completed')
        self.assertNotIn('error_type', self.records('decision_completed')[-1])
        self.assertTrue(self.records('native_turn_error')[-1]['will_retry'])

    def test_retry_cause_is_not_assumed_to_be_final_failure(self):
        self.notify(retry=True)
        self.complete()
        self.assertEqual(self.records('decision_completed')[-1]['error_type'], 'unknown')

    def test_late_events_cannot_poison_a_new_decision(self):
        self.notify()
        self.complete()
        self.begin('turn-2', 3)
        self.notify(turn='turn-1')
        self.complete(turn='turn-1')
        self.assertEqual(len(self.records('decision_completed')), 1)
        self.assertEqual(len(self.records('native_turn_error')), 1)
        self.assertEqual(self.router.threads['task']['status'], 'inProgress')
        self.assertNotIn('error_type', self.router.threads['task'])
        self.complete('completed', turn='turn-2')
        self.assertNotIn('error_type', self.records('decision_completed')[-1])

    def test_interruption_is_not_a_failed_turn_cause(self):
        self.notify(retry=True)
        self.complete('interrupted')
        self.assertNotIn('error_type', self.records('decision_completed')[-1])

    def test_rpc_rejection_does_not_persist_arbitrary_code_or_message(self):
        self.complete('completed')
        for code in (-32603, 'PRIVATE'):
            self.router.client_line(wire({'id': 3, 'method': 'turn/start', 'params': {'threadId': 'task',
                'model': 'gpt-6-luna', 'effort': 'low', 'input': [{'type': 'text', 'text': 'Traduce hola'}]}}))
            self.router.server_line(wire({'id': 3, 'error': {'code': code, 'message': 'PRIVATE'}}))
            result = self.records('decision_rejected')[-1]
            self.assertEqual(result['error_type'], 'turn_rejected')
            self.assertEqual(result.get('error_code'), code if type(code) is int else None)
        self.assertNotIn('PRIVATE', (self.root / 'state/history.jsonl').read_text())

    def test_generic_thread_status_preserves_known_native_cause(self):
        self.complete(error={'codexErrorInfo': 'usageLimitExceeded'})
        self.router.server_line(wire({'method': 'thread/status/changed', 'params': {
            'threadId': 'task', 'status': {'type': 'error'}}}))
        self.assertEqual(self.records('decision_error')[-1]['error_type'], 'usageLimitExceeded')

    def test_side_chat_errors_are_not_persisted(self):
        self.router.temporary_threads.add('task')
        self.notify()
        self.complete()
        self.assertFalse(self.records('native_turn_error'))
        self.assertFalse(self.records('decision_completed'))

    def test_jev_cannot_downgrade_open_review(self):
        self.complete('completed')
        config = self.router.config_path
        config.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES, 'routing_engine': 'jev'}))
        for model, effort in [('gpt-6-luna', 'low'), ('gpt-6.1-sol', 'high')]:
            with self.subTest(model=model), patch('router.run_jev', return_value={
                    'engine': 'jev', 'status': 'ok', 'route': {'model': model, 'effort': effort}}):
                self.router.pending.clear()
                request = wire({'id': 3, 'method': 'turn/start', 'params': {'threadId': 'task',
                    'model': 'gpt-6-luna', 'effort': 'low', 'input': [{'type': 'text', 'text': 'Haz una revision de como esta iendo'}]}})
                actual = json.loads(self.router.client_line(request))['params']
                self.assertEqual((actual['model'], actual['effort']), ('gpt-6.1-sol', 'high'))


if __name__ == '__main__':
    unittest.main()
