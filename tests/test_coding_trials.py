from tests.grader_sandbox import INTEGRATION
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests import coding_trials as grading
from tests.run_coding_trials import run_trials

CONFIDENCE_REFERENCE='''import math
def confidence(response):
    if not isinstance(response,dict):return None
    values=[]
    for path in [('confidence',),('answers','route','confidence'),('providerMetadata','typesafe','confidence','route')]:
        value=response
        for key in path:
            value=value.get(key) if isinstance(value,dict) else None
        if type(value) in (int,float) and math.isfinite(value) and 0<=value<=1:values.append(value)
    return min(values) if values else None
'''
TRANSITION_REFERENCE='''def transition(current,target,effort,active_turn,catalog):
    models=('gpt-6-luna','gpt-6.1-sol','gpt-6-astra')
    if current not in models or target not in models or not isinstance(catalog,dict) or not isinstance(catalog.get(target),list) or effort not in catalog[target]:
        return {'action':'reject','reason':'unsupported_route'}
    if active_turn and current!=target:
        return {'action':'defer','reason':'astra_boundary' if 'gpt-6-astra' in (current,target) else 'review_boundary'}
    return {'action':'apply','reason':'allowed'}
'''


class CodingTrialTests(unittest.TestCase):
    def test_frozen_cases_and_strict_duplicate_json_contract(self):
        self.assertEqual(len(grading.cases()),3)
        self.assertEqual(grading.check_answer('telemetry-review','{"findings":[],"findings":[]}'),{'json_contract':False})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'coding_trial_cases.json').write_text('{}');(root/'coding_grader_worker.py').write_text('changed')
            with patch.object(grading,'HERE',root),self.assertRaises(ValueError):grading.cases()

    def test_generated_code_contract_rejects_io_dynamic_execution_and_introspection(self):
        for source in ('import os\ndef f():return os.environ', 'def f():return open("secret")',
                       'def f():return (1).__class__', 'def f():return eval("1")',
                       '@print\ndef f():return 1', 'class C: pass'):
            self.assertFalse(grading.source_contract(source),source)
        self.assertTrue(grading.source_contract(CONFIDENCE_REFERENCE))

    def test_review_requires_all_defects_no_false_positives_and_no_duplicates(self):
        good=list(grading.REVIEW_CODES)
        checks=grading.check_answer('telemetry-review',json.dumps({'findings':good}))
        self.assertTrue(all(checks.values()))
        self.assertFalse(grading.check_answer('telemetry-review',json.dumps({'findings':good[:-1]}))['all_defects_found'])
        self.assertFalse(grading.check_answer('telemetry-review',json.dumps({'findings':good+['RAW_SECRET_PERSISTENCE']}))['no_false_positives'])
        self.assertFalse(grading.check_answer('telemetry-review',json.dumps({'findings':good+good[:1]}))['no_duplicate_findings'])

    def test_runner_rotates_order_retains_failure_and_never_activates(self):
        requests=[]
        def fake(**kw):
            requests.append((kw['exercise']['id'],kw['model']))
            return {'output_check':len(requests)!=1,'failure':None,'native_thread_total_tokens':{'inputTokens':10}}
        with tempfile.TemporaryDirectory() as d,patch('tests.run_coding_trials.run',side_effect=fake),patch.object(grading,'sandbox_controls',return_value={'synthetic_mock':True}),patch('builtins.print'):
            report=run_trials(Path(d)/'new',9)
        self.assertEqual(len(requests),9)
        self.assertEqual([m for c,m in requests][3:6],['gpt-6.1-sol','gpt-6-astra','gpt-6-luna'])
        self.assertTrue(report['complete_design']);self.assertEqual(report['passed'],8)
        self.assertFalse(report['attempts'][0]['output_check'])
        self.assertFalse(report['policy_activation_eligible'])
        self.assertEqual(report['complete_inference_cost_coverage'],'unknown')

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_sandbox_blocks_sentinel_read_writes_and_network(self):
        self.assertTrue(all(grading.sandbox_controls().values()))

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_confidence_reference_passes_and_buggy_probability_rounding_fails(self):
        self.assertTrue(all(grading.grade_source('confidence-repair',CONFIDENCE_REFERENCE).values()))
        bad="def confidence(response):\n    return round(response.get('confidence', response['choices'][0]['probability']),1)\n"
        checks=grading.grade_source('confidence-repair',bad)
        self.assertFalse(checks['edge_cases']);self.assertFalse(checks['probability_not_confidence'])

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_transition_reference_passes_and_removed_boundary_fails(self):
        self.assertTrue(all(grading.grade_source('transition-implementation',TRANSITION_REFERENCE).values()))
        bad="def transition(current,target,effort,active_turn,catalog):\n    return {'action':'apply','reason':'allowed'}\n"
        checks=grading.grade_source('transition-implementation',bad)
        self.assertFalse(checks['astra_boundary']);self.assertFalse(checks['review_boundary'])

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_nonterminating_candidate_has_bounded_execution(self):
        result=grading.grade_source('confidence-repair','def confidence(response):\n    while True:pass\n')
        self.assertFalse(result['execution'])


if __name__=='__main__':unittest.main()
