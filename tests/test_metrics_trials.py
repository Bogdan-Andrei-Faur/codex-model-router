import copy
import sys
import unittest

from tests import metrics_trials as grading
from tests.run_metrics_trials import admissible


class MetricsTrialTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_frozen_vectors_reject_regressions_and_accept_reference(self):
        for case in grading.manifest()['cases']:
            with self.subTest(case=case['id']):
                self.assertFalse(all(grading.grade(case, case['files']).values()))
                self.assertTrue(all(grading.grade(case, {'subject.py': case['reference_source']}).values()))

    def test_unsafe_source_never_runs(self):
        case = grading.manifest()['cases'][0]
        self.assertEqual(grading.grade(case, {'subject.py': 'import os\ndef x(): return os.environ\n'}), {'source_contract': False})

    def test_quality_failure_is_measurable_but_missing_evidence_is_not(self):
        checks = {k: True for k in grading.CHECKS-{'execution'}}
        row = dict(quality_admissible=True, status='finished', terminal='completed', tool_trace_complete=True,
                   inference_requests=1, denied_native_requests=0, checks=checks, workflow_complete=True,
                   output_check=True, requested_model='gpt-6-luna', requested_effort='high',
                   posterior_model_log_records={'gpt-6-luna': 3}, native_catalog={'gpt-6-luna': ['high']})
        self.assertTrue(admissible(row))
        failed = copy.deepcopy(row); failed['checks']['identity_or_provenance'] = False; failed['output_check'] = False
        self.assertTrue(admissible(failed))
        for invalid in (dict(row, posterior_model_log_records={}), dict(row, inference_requests=True),
                        dict(row, tool_trace_complete=False), dict(row, harness_invalid=True),
                        dict(row, output_check=False)):
            self.assertFalse(admissible(invalid))
