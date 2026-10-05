import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import token_counter_trials as grading, trial_tool_evidence
from tests.run_token_counter_trials import PAIRS, run_trials, safe_choice

REFERENCE = "import math\n\ndef token_count(value):\n    if type(value) is int:\n        count = value\n    elif type(value) is float:\n        if not math.isfinite(value) or not value.is_integer():\n            return None\n        count = int(value)\n    elif type(value) is str:\n        text = value.strip()\n        if text.startswith('+'):\n            text = text[1:]\n        if not 1 <= len(text) <= 10 or any(c not in '0123456789' for c in text):\n            return None\n        count = int(text)\n    else:\n        return None\n    return count if 0 <= count <= 1000000000 else None\n"

class TokenOracleTests(unittest.TestCase):
    def test_exact_reserved_snapshot_and_original_malformed_failure(self):
        manifest = grading.manifest(); case = manifest['cases'][0]
        source = case['files']['counter.py']
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), manifest['origin']['function_sha256'])
        self.assertEqual(case['split'], 'held_out')
        checks = grading.grade(case, case['files'])
        self.assertTrue(checks['valid_counters']); self.assertFalse(checks['malformed_unknown'])
        self.assertTrue(checks['no_mutation'])

    def test_reference_and_mutants(self):
        case = grading.cases()[0]
        self.assertTrue(all(grading.grade(case, {'counter.py': REFERENCE}).values()))
        mutants = [
            REFERENCE.replace('type(value) is int', 'isinstance(value, int)'),
            REFERENCE.replace('or not value.is_integer()', ''),
            REFERENCE.replace("any(c not in '0123456789' for c in text)", 'not text.isdigit()'),
            REFERENCE.replace('1000000000', '1000000001'),
            REFERENCE.replace('len(text) <= 10', 'len(text) <= 5000'),
            REFERENCE.replace('return None', 'return 0'),
        ]
        for source in mutants:
            checks = grading.grade(case, {'counter.py': source})
            self.assertNotIn('execution', checks); self.assertFalse(all(checks.values()))

    def test_workspace_fail_repair_pass_without_payload_retention(self):
        case = grading.cases()[0]
        self.assertEqual(grading.grade(case, {'counter.py': 'import os'}), {'source_contract': False})
        owned = trial_tool_evidence.Workspace(case, grading.grade, grading.CHECKS)
        try:
            owned.handle('trial_read', {'path': 'counter.py'})
            self.assertFalse(owned.handle('trial_test', {})[1]['passed'])
            owned.handle('trial_write', {'path': 'counter.py', 'source': REFERENCE})
            self.assertTrue(owned.handle('trial_test', {})[1]['passed'])
            report = owned.report()
            self.assertEqual([e['passed'] for e in report['tool_events'] if e['tool']=='trial_test'], [False, True])
            self.assertTrue(report['workflow_complete']); self.assertFalse(report['harness_invalid'])
            self.assertNotIn(REFERENCE, json.dumps(report)); path = owned.root
        finally:
            owned.close()
        self.assertFalse(path.exists())


class TokenCampaignTests(unittest.TestCase):
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
            with patch('tests.run_token_counter_trials.native_catalog', return_value={m: ['high'] for m, _ in PAIRS}), \
                 patch('tests.run_token_counter_trials.sandbox_controls', return_value={}), \
                 patch('tests.run_token_counter_trials._run_jev', side_effect=provider) as jev, \
                 patch('tests.run_token_counter_trials.run_multifile_trials.run_arm', side_effect=native) as arm, \
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
                 patch('tests.run_token_counter_trials.native_catalog', return_value={m: ['high'] for m, _ in PAIRS}), \
                 patch('tests.run_token_counter_trials.sandbox_controls', return_value={}), \
                 patch('tests.run_token_counter_trials._run_jev', return_value={'status': 'unavailable'}), \
                 patch('tests.run_token_counter_trials.run_multifile_trials.run_arm', return_value=dict(self.sample(PAIRS[0][0]), **extra)) as call, \
                 patch('builtins.print'):
                report = run_trials(Path(tmp)/'new')
            self.assertEqual(call.call_count, 1)
            self.assertEqual(report['native_turn_requests'], 1)
            self.assertEqual(report['quality_attempts'], 0); self.assertTrue(report['campaign_stopped'])
        with tempfile.TemporaryDirectory() as tmp, \
             patch('tests.run_token_counter_trials.native_catalog', return_value={PAIRS[0][0]: ['high']}), \
             patch('tests.run_token_counter_trials.sandbox_controls', return_value={}), \
             patch('tests.run_token_counter_trials._run_jev') as jev, \
             patch('tests.run_token_counter_trials.run_multifile_trials.run_arm') as native:
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
