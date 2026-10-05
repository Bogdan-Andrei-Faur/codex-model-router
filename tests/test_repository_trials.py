import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from tests import repository_trials as grading, trial_tool_evidence
from tests.run_repository_trials import PAIRS, run_trials, safe_choice

REFERENCE = '''def available_routes(routes, catalog):
    result = deepcopy(routes)
    for route in result.values():
        model = route.get("model")
        if model not in catalog:
            for alternative in ALTERNATIVES.get(model, ()):
                efforts = catalog.get(alternative)
                if isinstance(efforts, (list, tuple, set)) and route.get("effort") in efforts:
                    route["model"] = alternative
                    break
    return result
'''


class RepositoryOracleTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_snapshot_function_provenance_and_original_failure_are_explicit(self):
        manifest = grading.manifest(); case = manifest['cases'][0]
        source = case['files']['catalog.py']
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), manifest['origin']['function_sha256'])
        self.assertEqual(len(manifest['origin']['commit']), 40)
        self.assertEqual(case['split'], 'adjustment')
        checks = grading.grade(case, case['files'])
        self.assertIs(checks['source_contract'], True)
        self.assertIs(checks['compatible_fallback'], False)
        self.assertIs(checks['no_mutation'], True)

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_reference_passes_and_targeted_mutants_are_not_free_successes(self):
        case = grading.cases()[0]
        self.assertTrue(all(grading.grade(case, {'catalog.py': REFERENCE}).values()))
        mutants = [
            REFERENCE.replace('result = deepcopy(routes)', 'result = dict(routes)'),
            REFERENCE.replace('and route.get("effort") in efforts', ''),
            REFERENCE.replace('(list, tuple, set)', '(list, tuple, set, str, dict)'),
            REFERENCE.replace('                    break\n', ''),
            REFERENCE.replace('if model not in catalog:', 'if True:'),
            REFERENCE.replace('                    break', '                    route["effort"] = "medium"\n                    break'),
        ]
        for source in mutants:
            with self.subTest(mutant=hashlib.sha256(source.encode()).hexdigest()):
                checks = grading.grade(case, {'catalog.py': source})
                self.assertNotIn('execution', checks)
                self.assertFalse(all(checks.values()))

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_source_guards_and_workspace_trace_keep_generated_payloads_ephemeral(self):
        case = grading.cases()[0]
        self.assertEqual(grading.grade(case, {'catalog.py': 'import os'}), {'source_contract': False})
        owned = trial_tool_evidence.Workspace(case, grading.grade, grading.CHECKS)
        try:
            owned.handle('trial_read', {'path': 'catalog.py'})
            self.assertFalse(owned.handle('trial_test', {})[1]['passed'])
            owned.handle('trial_write', {'path': 'catalog.py', 'source': REFERENCE})
            self.assertTrue(owned.handle('trial_test', {})[1]['passed'])
            report = owned.report(); tests = [e for e in report['tool_events'] if e['tool'] == 'trial_test']
            self.assertEqual([e['passed'] for e in tests], [False, True])
            self.assertTrue(report['workflow_complete']); self.assertFalse(report['harness_invalid'])
            self.assertNotIn(REFERENCE, json.dumps(report))
            path = owned.root
        finally:
            owned.close()
        self.assertFalse(path.exists())


class RepositoryCampaignTests(unittest.TestCase):
    def sample(self, model, passed=True):
        return {'requested_model': model, 'requested_effort': 'high', 'status': 'finished',
                'terminal': 'completed', 'inference_requests': 1, 'quality_admissible': True,
                'tool_trace_complete': True, 'denied_native_requests': 0, 'workflow_complete': True,
                'output_check': passed, 'checks': {k: passed for k in grading.CHECKS-{'execution'}},
                'posterior_model_log_records': {model: 1}, 'native_catalog': {model: ['high']}}

    def test_classifier_intent_precedes_answers_and_fixed_design_and_negatives_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'new'; order = []
            original_read = Path.read_text
            def provider(config, state, payload, choices):
                report = json.loads((output/'report.json').read_text())
                self.assertEqual(len(report['planned_turns']), 2)
                self.assertEqual(report['attempts'], [])
                self.assertEqual(report['provider_attempts'][0]['status'], 'intent')
                self.assertEqual({(r['model'], r['effort']) for r in choices.values()}, set(PAIRS))
                order.append('jev')
                return {'status': 'ok', 'route': {'model': PAIRS[0][0], 'effort': 'high'}, 'confidence': .8}
            def native(case, model, effort, workspace, dynamic_specs):
                report = json.loads((output/'report.json').read_text())
                self.assertEqual(report['attempts'][-1]['status'], 'intent')
                self.assertEqual(report['provider_attempts'][0]['status'], 'ok')
                order.append(model)
                return self.sample(model, passed=model != PAIRS[0][0])
            with patch('tests.run_repository_trials.native_catalog', return_value={m: ['high'] for m, _ in PAIRS}), \
                 patch('tests.run_repository_trials.sandbox_controls', return_value={}), \
                 patch('tests.run_repository_trials._run_jev', side_effect=provider) as jev, \
                 patch('tests.run_repository_trials.run_multifile_trials.run_arm', side_effect=native) as arm, \
                 patch('pathlib.Path.read_text', autospec=True, side_effect=lambda p, *a, **k: '{}' if p.name == 'config.local.json' else original_read(p, *a, **k)), \
                 patch('builtins.print'):
                report = run_trials(output)
        self.assertEqual(order, ['jev', *[p[0] for p in PAIRS]])
        self.assertEqual((jev.call_count, arm.call_count), (1, 2))
        self.assertEqual((report['quality_attempts'], report['passed']), (2, 1))
        self.assertIs(report['provider_attempts'][0]['measured_exercise_pass'], False)
        self.assertTrue(report['complete_design']); self.assertFalse(report['policy_activation_eligible'])

    def test_bad_grader_or_catalog_stops_without_retry_or_success_denominator(self):
        for extra in ({'harness_invalid': True}, {'tool_trace_complete': False}, {'checks': {'source_contract': True}},
                      {'posterior_model_log_records': {'gpt-6-astra': 1}}):
            with tempfile.TemporaryDirectory() as tmp, \
                 patch('tests.run_repository_trials.native_catalog', return_value={m: ['high'] for m, _ in PAIRS}), \
                 patch('tests.run_repository_trials.sandbox_controls', return_value={}), \
                 patch('tests.run_repository_trials._run_jev', return_value={'status': 'unavailable'}), \
                 patch('tests.run_repository_trials.run_multifile_trials.run_arm', return_value=dict(self.sample(PAIRS[0][0]), **extra)) as call, \
                 patch('builtins.print'):
                report = run_trials(Path(tmp)/'new')
            self.assertEqual(call.call_count, 1)
            self.assertEqual(report['native_turn_requests'], 1)
            self.assertEqual(report['quality_attempts'], 0); self.assertTrue(report['campaign_stopped'])
        with tempfile.TemporaryDirectory() as tmp, \
             patch('tests.run_repository_trials.native_catalog', return_value={PAIRS[0][0]: ['high']}), \
             patch('tests.run_repository_trials.sandbox_controls', return_value={}), \
             patch('tests.run_repository_trials._run_jev') as jev, \
             patch('tests.run_repository_trials.run_multifile_trials.run_arm') as native:
            report = run_trials(Path(tmp)/'new')
        self.assertEqual(jev.call_count, 0); self.assertEqual(native.call_count, 0)
        self.assertTrue(report['campaign_stopped'])

    def test_quota_and_provider_payload_privacy_guards(self):
        for native, provider in ((1, 1), (2, 2), (True, 1), (2, True)):
            with self.assertRaises(ValueError):
                run_trials(Path('unused'), native, provider)
        choices = {'first': {'model': PAIRS[0][0], 'effort': 'high'}}
        source = {'status': 'ok', 'route': dict(choices['first']), 'confidence': True,
                  'engine_provider_cost_usd': float('nan'), 'engine_input_tokens': True,
                  'private_error': 'PRIVATE-DO-NOT-COPY'}
        result = safe_choice(source, choices)
        self.assertIsNone(result['confidence']); self.assertNotIn('provider_reported_classifier_usd', result)
        self.assertNotIn('engine_input_tokens', result)
        self.assertNotIn('PRIVATE-DO-NOT-COPY', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
