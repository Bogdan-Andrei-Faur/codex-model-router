import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.evidence_inventory import inventory


class EvidenceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'state').mkdir()
        self.reports = {}
        self.plan = {'schema': 'evidence-inventory-plan/1', 'campaigns': []}

    def campaign(self, ident, rows, purpose='comparison', case_hash='a'*64):
        report = {'schema': 'isolated-multifile-trials/1', 'case_sha256': case_hash,
                  'grader_sha256': 'b'*64, 'attempts': rows}
        data = json.dumps(report).encode()
        path = 'state/'+ident+'.json'
        (self.root/path).write_bytes(data)
        spec = {'id': ident, 'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
                'purpose': purpose, 'schema': report['schema'], 'case_sha256': case_hash,
                'grader_sha256': 'b'*64, 'checks': {'fixture': ['result']}}
        if purpose == 'invalid_harness':
            spec['reviewed_exclusion'] = 'allowed_paths_not_exposed'
        self.plan['campaigns'].append(spec)
        self.reports[ident] = report
        return spec

    def row(self, serial=1, passed=True):
        return {'case_id': 'fixture', 'requested_model': 'gpt-6-luna',
                'requested_effort': 'high', 'attempt': 1, 'serial': serial,
                'inference_requests': 1, 'terminal': 'completed', 'status': 'finished',
                'quality_admissible': True, 'denied_native_requests': 0,
                'workflow_complete': True, 'checks': {'result': passed}, 'output_check': passed,
                'native_thread_total_tokens': {'inputTokens': 100, 'cachedInputTokens': 80, 'outputTokens': 10},
                'posterior_model_log_records': {'gpt-6-luna': 5}}

    def run_inventory(self, jev=None):
        p = self.root/'state/jev.json'; data = b'{}'; p.write_bytes(data)
        self.plan['jev'] = {'path': 'state/jev.json', 'sha256': hashlib.sha256(data).hexdigest(),
                            'native_campaign': self.plan['campaigns'][0]['id']}
        with patch('tests.evidence_inventory.link_measured', return_value={'attempts': jev or []}) as linker:
            report = inventory(self.root, self.plan)
            linker.assert_called_once()
        return report

    def test_repetitions_and_instrument_do_not_inflate_fixture_or_quality_counts(self):
        self.campaign('first', [self.row(1), self.row(2)])
        self.campaign('repeat', [self.row(3)])
        self.campaign('instrument', [self.row(4)], 'instrument')
        report = self.run_inventory()
        self.assertEqual(report['distinct_measured_fixtures'], 1)
        self.assertEqual(report['by_purpose']['comparison']['measured_outcomes'], 3)
        self.assertEqual(report['by_purpose']['instrument']['measured_outcomes'], 0)
        self.assertEqual(report['by_purpose']['instrument']['native_requests'], 1)
        self.assertFalse(report['policy_activation_eligible'])

    def test_negatives_count_but_partial_checks_and_boolean_attempts_remain_unknown(self):
        negative = self.row(1, False)
        partial = self.row(2); partial['checks'] = {}
        nonbool = self.row(3); nonbool['checks']['result'] = 1
        boolean = self.row(4); boolean['attempt'] = True
        boolean_request = self.row(5); boolean_request['inference_requests'] = True
        self.campaign('mixed', [negative, partial, nonbool, boolean, boolean_request])
        stats = self.run_inventory()['by_purpose']['comparison']
        self.assertEqual((stats['failed'], stats['passed'], stats['unknown_outcomes']), (1, 0, 4))
        self.assertEqual((stats['native_requests'], stats['unknown_native_requests']), (4, 1))

    def test_historical_invalidation_overrides_automatic_pass_without_losing_tokens(self):
        spec = self.campaign('invalid', [self.row()], 'invalid_harness')
        audit = {'quality_admissible': False, 'original_report_sha256': spec['sha256']}
        data = json.dumps(audit).encode(); (self.root/'state/audit.json').write_bytes(data)
        spec['exclusion_audit'] = {'path': 'state/audit.json', 'sha256': hashlib.sha256(data).hexdigest()}
        stats = self.run_inventory()['by_purpose']['invalid_harness']
        self.assertEqual((stats['native_requests'], stats['measured_outcomes']), (1, 0))
        self.assertEqual(stats['inputTokens'], 100)
        spec['exclusion_audit']['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'frozen_report_mismatch'):
            self.run_inventory()

    def test_duplicate_files_and_overlapping_cumulative_snapshots_are_rejected(self):
        first = self.campaign('first', [self.row(1)])
        second = self.campaign('second', [self.row(1), self.row(2)])
        with self.assertRaisesRegex(ValueError, 'overlapping_execution_records'):
            self.run_inventory()
        self.plan['campaigns'] = [first, copy.deepcopy(first)]
        self.plan['campaigns'][1]['id'] = 'alias'
        with self.assertRaisesRegex(ValueError, 'invalid_campaign_membership'):
            self.run_inventory()

    def test_original_digest_origin_and_safe_path_are_checked(self):
        spec = self.campaign('first', [self.row()])
        spec['case_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'invalid_campaign_origin'):
            self.run_inventory()
        spec['case_sha256'] = 'a'*64
        spec['path'] = 'state/../state/first.json'
        with self.assertRaisesRegex(ValueError, 'invalid_frozen_reference'):
            self.run_inventory()
        spec['path'] = 'state/link.json'
        (self.root/'state/link.json').symlink_to(self.root/'state/first.json')
        with self.assertRaisesRegex(ValueError, 'unsafe_frozen_reference'):
            self.run_inventory()

    def test_bad_token_coverage_does_not_become_zero_cost_or_hide_attempts(self):
        invalid = self.row(1); invalid['native_thread_total_tokens']['cachedInputTokens'] = 101
        missing = self.row(2); missing.pop('native_thread_total_tokens')
        preflight = self.row(3); preflight['inference_requests'] = 0
        self.campaign('first', [invalid, missing, preflight])
        stats = self.run_inventory()['by_purpose']['comparison']
        self.assertEqual((stats['attempts'], stats['native_requests'], stats['preflight_attempts']), (3, 2, 1))
        self.assertEqual(stats['token_covered_requests'], 0)
        self.assertNotIn('inputTokens', stats)

    def test_consistent_model_tags_and_reconciled_usage_are_not_strict_identity(self):
        row = self.row()
        row['raw_usage_matches_native_total'] = True
        row['native_raw_evidence'] = {'responses_missing_usage': 0, 'counts': {'joined': 1},
                                     'response_tokens_sum': dict(row['native_thread_total_tokens'])}
        self.campaign('first', [row])
        stats = self.run_inventory()['by_purpose']['comparison']
        self.assertEqual(stats['response_usage_reconciled_requests'], 1)
        self.assertEqual(stats['strict_model_identity_requests'], 0)

    def test_jev_joins_recomputed_and_single_model_positive_not_choice_calibration(self):
        self.campaign('first', [self.row()])
        report = self.run_inventory([
            {'eligible_model_count': 1, 'independent_model_judgment_possible': False, 'measured_exercise_pass': True},
            {'eligible_model_count': 2, 'independent_model_judgment_possible': True, 'measured_exercise_pass': None}])
        self.assertEqual(report['jev']['linked_outcomes'], 1)
        self.assertEqual(report['jev']['multiple_model_choices'], 1)
        self.assertEqual(report['jev']['multiple_model_linked_outcomes'], 0)
        self.assertFalse(report['jev']['calibration_ready'])
        report = self.run_inventory([
            {'eligible_model_count': 2, 'independent_model_judgment_possible': True, 'measured_exercise_pass': False}])
        self.assertEqual(report['jev']['multiple_model_linked_failures'], 1)

    def test_private_unknown_fields_never_copied_to_output(self):
        row = self.row(); row.update(prompt='PRIVATE-PROMPT', secret='PRIVATE-SECRET', title='PRIVATE-TITLE')
        self.campaign('first', [row])
        text = json.dumps(self.run_inventory())
        for marker in ('PRIVATE-PROMPT', 'PRIVATE-SECRET', 'PRIVATE-TITLE'):
            self.assertNotIn(marker, text)
        self.assertEqual(self.reports['first']['attempts'][0]['prompt'], 'PRIVATE-PROMPT')


if __name__ == '__main__':
    unittest.main()
