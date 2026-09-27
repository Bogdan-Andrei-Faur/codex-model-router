"""Synthetic reproductions of the 0.4.1 decision shapes, not saved user prompts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from decision_engines import candidate_routes
from routing import DEFAULT_ROUTES, EFFORTS, select_route_details
from router import Router
from workload import response_summary, merge_contract, effective_context, context_for_engine
from state_store import persist_task, read_records
from task_modes import mode_path


def wire(value):
    return (json.dumps(value) + '\n').encode()


class BalancedPolicyTests(unittest.TestCase):
    def test_each_band_excludes_both_underpowered_and_unjustified_expensive_options(self):
        cases = [
            ('Traduce al inglés: hola', {'simple', 'normal'}),
            ('Gracias', {'simple', 'normal'}),
            ('Dime los contadores de la telemetría', {'simple', 'normal'}),
            ('Cambia solo el color del icono', {'simple', 'normal'}),
            ('Crea un formulario en la interfaz', {'normal'}),
            ('Explica qué hace esta función', {'normal'}),
            ('Configure authentication for the application', {'complex'}),
            ('Ahora arregla la autorización del servicio', {'complex'}),
            ('Tengo una duda sobre esto', {'complex'}),
            ('¿Por qué ocurre?', {'complex'}),
            ('Revisa cómo va el proyecto', {'complex'}),
            ('Audita la autorización del servicio', {'critical'}),
            ('Fix a vulnerability in authentication', {'critical'}),
            ('Investiga la pérdida de datos en producción', {'critical'}),
            ('Rediseña toda la UX', {'critical'}),
        ]
        catalog = {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                _, policy = select_route_details(prompt, DEFAULT_ROUTES, 'critical', 'xhigh')
                candidates = candidate_routes(DEFAULT_ROUTES, catalog, policy)
                self.assertEqual({r['tier'] for r in candidates.values()}, expected)
                if expected == {'complex'}:
                    self.assertTrue(all(EFFORTS.index(r['effort']) >= EFFORTS.index('high') for r in candidates.values()))

    def test_previous_luna_and_astra_do_not_override_unknown_scope(self):
        for previous in ('simple', 'normal', 'complex', 'critical'):
            for prompt in ('Tengo una duda sobre esto', '¿Por qué ocurre?', 'Ok, arréglalo'):
                with self.subTest(previous=previous, prompt=prompt):
                    route, _ = select_route_details(prompt, DEFAULT_ROUTES, previous, 'low')
                    self.assertEqual(route, {'model': 'gpt-5.6-sol', 'effort': 'high'})

    def test_known_pending_work_can_continue_on_terra_or_astra(self):
        for floor in ('normal', 'complex', 'critical'):
            route, _ = select_route_details('Adelante', DEFAULT_ROUTES, 'simple', 'low',
                response_context={'implementation_pending': True, 'work_floor': floor})
            self.assertEqual(route, DEFAULT_ROUTES[floor])

    def test_contracts_distinguish_routine_auth_from_concrete_risk(self):
        for prompt, floor in [('Falta implementar autenticación', 'complex'),
                              ('Falta corregir una vulnerabilidad', 'critical')]:
            contract = merge_contract(None, response_summary(prompt))
            self.assertEqual((contract['floor'], contract['version']), (floor, 2))

    def test_legacy_floor_is_uncertain_without_rewriting_history(self):
        row = {'task_floor': 'critical', 'task_contract': {'status': 'pending', 'floor': 'critical', 'plan_steps': ['verify']}}
        context = effective_context(row)
        self.assertEqual(context['work_floor'], 'complex')
        self.assertTrue(context['legacy_uncertain'])
        self.assertEqual(row['task_contract']['floor'], 'critical')
        row['task_contract']['version'] = 2
        self.assertEqual(effective_context(row)['work_floor'], 'critical')

    def test_explicit_final_remaining_scope_can_lower_contract_but_progress_cannot(self):
        old = merge_contract(None, response_summary('Queda una vulnerabilidad por corregir'))
        self.assertEqual(merge_contract(old, response_summary('Falta investigar la integración'))['floor'], 'critical')
        summary = response_summary('La vulnerabilidad está resuelta. Solo queda documentar el cambio.')
        self.assertEqual(merge_contract(old, {**summary, 'response_kind': 'progress'})['floor'], 'critical')
        updated = merge_contract(old, summary)
        self.assertEqual(updated['floor'], 'normal')
        self.assertEqual(effective_context({'task_contract': updated, 'response_context': summary})['work_floor'], 'normal')

    def test_context_export_contains_only_known_symbols(self):
        context = {'implementation_pending': True, 'work_floor': 'complex', 'plan_steps': ['verify', 'PRIVATE', {}, 'verify'],
                   'title': 'PRIVATE', 'response_kind': 'PRIVATE', 'mentions_tests': 'PRIVATE'}
        self.assertEqual(context_for_engine(context), {'implementation_pending': True, 'work_floor': 'complex', 'plan_steps': ['verify']})


class BalancedBridgeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES, 'routing_engine': 'jev'}))
        self.router = Router(self.config, self.root / 'state')
        self.router.catalog = {r['model']: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        self.router.threads['t'] = {'name': 'Synthetic', 'provider': 'openai', 'model': 'gpt-5.6-luna',
                                  'effort': 'low', 'tier': 'simple', 'seen_turn': True}

    def request(self, prompt):
        return wire({'id': 10, 'method': 'turn/start', 'params': {'threadId': 't',
                    'model': 'gpt-5.6-luna', 'effort': 'low', 'input': [{'type': 'text', 'text': prompt}]}})

    def route(self, prompt, result):
        self.router.pending.clear()
        with patch('router.run_jev', return_value=result) as mock:
            actual = json.loads(self.router.client_line(self.request(prompt)))['params']
        return actual, mock

    def test_jev_luna_and_outage_cannot_reproduce_undersized_ambiguous_followup(self):
        for result in ({'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['simple']},
                       {'engine': 'jev', 'status': 'unavailable', 'engine_failure': 'timeout'}):
            for prompt in ('Tengo una duda sobre esto', '¿Por qué ocurre?'):
                actual, _ = self.route(prompt, result)
                self.assertEqual((actual['model'], actual['effort']), ('gpt-5.6-sol', 'high'))
        self.assertNotIn('task_contract', self.router.threads['t'])  # Uncertainty is not a new pending task.

    def test_ordinary_change_is_bounded_to_terra_for_every_jev_proposal(self):
        for tier in ('simple', 'normal', 'complex', 'critical'):
            actual, _ = self.route('Añade un campo al formulario', {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES[tier]})
            self.assertEqual(actual['model'], DEFAULT_ROUTES['normal']['model'])

    def test_retry_evidence_can_still_escalate_beyond_terra(self):
        actual, _ = self.route('Sigue fallando, corrige el formulario',
                               {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['complex']})
        self.assertEqual((actual['model'], actual['effort']),
                         (DEFAULT_ROUTES['complex']['model'], DEFAULT_ROUTES['complex']['effort']))

    def test_legacy_restart_context_is_sent_as_symbols_and_allows_sol(self):
        persist_task(self.root / 'state', 't', {'task_contract': {'status': 'pending', 'floor': 'critical', 'plan_steps': ['verify']}})
        restarted = Router(self.config, self.root / 'state')
        self.router.threads['t'].update(restarted.thread_categories['t'])
        actual, mock = self.route('¿Por qué ocurre?', {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['complex']})
        self.assertEqual(actual['model'], 'gpt-5.6-sol')
        state = mock.call_args.args[2]
        self.assertEqual(state['work_context']['plan_steps'], ['verify'])
        self.assertTrue(state['work_context']['legacy_uncertain'])

    def test_known_critical_context_preserves_astra_only_when_resumed(self):
        self.router.threads['t']['task_contract'] = merge_contract(None, response_summary('Falta corregir una vulnerabilidad'))
        actual, _ = self.route('Adelante', {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['simple']})
        self.assertEqual(actual['model'], 'gpt-6-astra')
        actual, mock = self.route('Añade un campo al formulario', {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['normal']})
        self.assertEqual(actual['model'], 'gpt-5.6-terra')
        self.assertEqual(mock.call_args.args[2]['work_context']['work_floor'], 'critical')
        self.assertNotIn('previous_response_context', mock.call_args.args[2])

    def test_new_task_clears_context_and_bounded_request_stays_light(self):
        self.router.threads['t']['task_contract'] = merge_contract(None, response_summary('Falta corregir una vulnerabilidad'))
        actual, mock = self.route('Nueva tarea: traduce hola', {'engine': 'jev', 'status': 'ok', 'route': DEFAULT_ROUTES['simple']})
        self.assertEqual(actual['model'], 'gpt-5.6-luna')
        self.assertNotIn('work_context', mock.call_args.args[2])

    def test_band_metadata_is_recorded_without_exported_context(self):
        self.route('Añade un campo al formulario', {'engine': 'jev', 'status': 'unavailable'})
        records = list(read_records(self.root / 'state/history.jsonl'))
        created = next(r for r in records if r['event'] == 'decision_created')
        self.assertEqual((created['quality_floor'], created['quality_ceiling']), ('normal', 'normal'))
        self.assertNotIn('Añade', str(records))
        self.assertNotIn('work_context', str(records))

    def test_manual_and_explicit_selection_still_override_bands(self):
        actual, mock = self.route('Usa Astra: añade un campo al formulario', {'engine': 'jev', 'status': 'unavailable'})
        self.assertEqual(actual['model'], 'gpt-6-astra')
        mock.assert_not_called()
        path = mode_path(self.root / 'state', 't')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'thread': 't', 'mode': 'manual'}))
        actual, mock = self.route('Revisa el proyecto', {'engine': 'jev', 'status': 'unavailable'})
        self.assertEqual(actual['model'], 'gpt-5.6-luna')
        mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
