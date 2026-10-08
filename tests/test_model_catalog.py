import copy
import json
from pathlib import Path
import tempfile
import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.routing.model_catalog import (MODELS, DEFAULT_ROUTES, LEGACY_ROUTES, migrate_config,
                           available_routes, estimate_standard_usage)
from codex_model_router.routing.routing import EFFORTS, explicit_model, select_route_details
from codex_model_router.bridge.router import Router
from codex_model_router.routing.decision_engines import candidate_routes


class ModelCatalogTests(unittest.TestCase):
    def test_only_unmodified_unversioned_defaults_migrate(self):
        config = {'routes': copy.deepcopy(LEGACY_ROUTES), 'enabled': False, 'jev': {'connection': 'vercel'}}
        migrated = migrate_config(config)
        self.assertEqual(migrated['routes'], DEFAULT_ROUTES)
        self.assertFalse(migrated['enabled'])
        self.assertEqual(migrated['jev'], config['jev'])
        self.assertEqual(config['routes'], LEGACY_ROUTES)
        self.assertEqual(migrate_config(migrated), migrated)
        config['routes']['simple']['effort'] = 'medium'
        self.assertEqual(migrate_config(config), config)
        config.update(routes=LEGACY_ROUTES, model_catalog_version='pinned')
        self.assertEqual(migrate_config(config), config)

    def test_exact_version_and_negation_quote_guards(self):
        for model in MODELS:
            with self.subTest(model=model):
                self.assertEqual(explicit_model('Usa '+model, DEFAULT_ROUTES)['model'], model)
        self.assertEqual(explicit_model('Usa Terra', DEFAULT_ROUTES)['model'], 'gpt-5.6-terra')
        for prompt in ('No uses gpt-6.1-sol', 'Traduce: "Usa gpt-6.1-sol"',
                       'Usa gpt-6.1-sol o gpt-6-sol', 'Usa gpt-99-sol'):
            self.assertIsNone(explicit_model(prompt, DEFAULT_ROUTES))
        self.assertEqual(select_route_details('Usa gpt-6.1-sol con esfuerzo alto', DEFAULT_ROUTES)[0],
                         {'model': 'gpt-6.1-sol', 'effort': 'high'})
        self.assertEqual(explicit_model('Usa GPT-6.1 Sol', DEFAULT_ROUTES)['model'], 'gpt-6.1-sol')

    def test_new_phase_pairs_are_not_enabled_by_catalog_recognition(self):
        from codex_model_router.bridge.phase_tracking import can_switch_within_turn, transition_kind
        for source, target in [('gpt-6-luna', 'gpt-6.1-sol'), ('gpt-6.1-sol', 'gpt-6-luna')]:
            self.assertFalse(can_switch_within_turn(source, target))
            self.assertEqual(transition_kind(source, target), 'blocked_review_boundary')
        self.assertFalse(can_switch_within_turn('gpt-6-sol', 'gpt-6.1-sol'))
        self.assertTrue(can_switch_within_turn('gpt-6.1-sol', 'gpt-6.1-sol'))

    def test_fallbacks_are_known_and_do_not_mutate_config(self):
        catalog = {'gpt-6-sol': set(EFFORTS), 'gpt-5.6-luna': {'low'}}
        routes = available_routes(DEFAULT_ROUTES, catalog)
        self.assertEqual(routes['normal']['model'], 'gpt-6-sol')
        self.assertEqual(routes['simple']['model'], 'gpt-5.6-luna')
        custom = {'simple': {'model': 'custom', 'effort': 'low'}}
        self.assertEqual(available_routes(custom, catalog), custom)
        self.assertEqual(DEFAULT_ROUTES['normal']['model'], 'gpt-6.1-sol')

    def test_jev_labels_version_and_keeps_complex_effort_floor(self):
        _, policy = select_route_details('Investiga una condición de carrera', DEFAULT_ROUTES)
        catalog = {m: set(EFFORTS) for m in MODELS}
        choices = candidate_routes(DEFAULT_ROUTES, catalog, policy)
        self.assertTrue(choices)
        self.assertTrue(all(c['model'] == 'gpt-6.1-sol' and c['effort'] in ('high', 'xhigh') for c in choices.values()))
        self.assertTrue(all(c['label'].startswith('Sol 6.1') for c in choices.values()))

    def test_all_known_native_models_can_enter_automatic_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'config.json'
            path.write_text(json.dumps({'enabled': True, 'routes': DEFAULT_ROUTES}))
            router = Router(path, Path(tmp)/'state')
            router.catalog = {model: set(EFFORTS) for model in MODELS}
            for i, model in enumerate(MODELS):
                tid = str(i)
                router.threads[tid] = {'provider': 'openai', 'model': model}
                raw = (json.dumps({'id': i, 'method': 'turn/start', 'params': {'threadId': tid,
                    'model': model, 'input': [{'type': 'text', 'text': 'Traduce hola al inglés'}]}})+'\n').encode()
                self.assertEqual(json.loads(router.client_line(raw))['params']['model'], 'gpt-6-luna')
            router.threads['exact'] = {'provider': 'openai', 'model': 'gpt-6-astra'}
            raw = json.dumps({'id': 100, 'method': 'turn/start', 'params': {'threadId': 'exact',
                'input': [{'type': 'text', 'text': 'Usa gpt-6-sol'}]}}).encode()
            self.assertEqual(json.loads(router.client_line(raw))['params']['model'], 'gpt-6-sol')

    def test_standard_estimates_separate_cache_and_never_double_count_reasoning(self):
        metrics = {'inference_input_tokens': 1000, 'inference_cached_tokens': 600,
                   'inference_cache_write_tokens': 100, 'inference_output_tokens': 200,
                   'inference_reasoning_tokens': 180}
        estimate = estimate_standard_usage('gpt-6.1-sol', metrics)
        self.assertAlmostEqual(estimate['estimated_api_standard_usd'], .00291)
        self.assertAlmostEqual(estimate['estimated_codex_standard_credits'], .0715)
        self.assertEqual(estimate['estimate_basis'], 'standard_equivalent_not_billed')
        incomplete_cache = dict(metrics)
        incomplete_cache.pop('inference_cache_write_tokens')
        partial = estimate_standard_usage('gpt-6.1-sol', incomplete_cache)
        self.assertNotIn('estimated_api_standard_usd', partial)
        self.assertAlmostEqual(partial['estimated_codex_standard_credits'], .0715)
        for invalid in ({}, {**metrics, 'inference_cached_tokens': 1100},
                        {**metrics, 'inference_input_tokens': 300000}, {**metrics, 'inference_output_tokens': float('nan')}):
            self.assertEqual(estimate_standard_usage('gpt-6.1-sol', invalid), {})
        self.assertEqual(estimate_standard_usage('unknown', metrics), {})
