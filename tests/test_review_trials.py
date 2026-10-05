import copy
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from tests import review_trials as grading
from tests.run_review_trials import run_trials,design_trials

INTERVAL=[{'function':'B','args':{'interval':[1,3],'point':3}},
    {'function':'C','args':{'window':[0,5],'blocked':[[10,15]]}},
    {'function':'F','args':{'count':0,'size':3}}]
ORDERED=[{'function':'B','args':{'values':[1,2],'count':0}},
    {'function':'D','args':{'base':1,'attempts':1,'cap':10}}]


class ReviewGraderTests(unittest.TestCase):
    def test_allowed_paths_are_exposed_before_native_calls(self):
        for case in grading.cases():
            schema=grading.tools(case)[0]['tools'][0]['inputSchema']['properties']['path']
            self.assertEqual(set(schema['enum']),set(case['files']))
            for path in case['files']:self.assertIn(path,case['request'])

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_known_counterexamples_pass_and_empty_submissions_miss_defects(self):
        for case,findings in zip(grading.cases(),(INTERVAL,ORDERED)):
            with self.subTest(case=case['id']):
                score=grading.grade(case,findings)
                self.assertTrue(all(score['checks'].values()))
                self.assertEqual(score['verified_defects'],len(findings))
                empty=grading.grade(case,[])
                self.assertEqual(empty['missed_defects'],len(findings))
                self.assertFalse(empty['checks']['all_defects_found'])

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_false_positive_duplicate_and_invalid_witness_are_distinct(self):
        case=grading.cases()[0]
        positive=grading.grade(case,INTERVAL+[{'function':'A','args':{'intervals':[[1,3]]}}])
        self.assertEqual(positive['false_positives'],1)
        self.assertEqual(positive['unexpected_counterexamples'],0)
        self.assertFalse(positive['checks']['no_false_positives'])
        duplicate=grading.grade(case,INTERVAL+[INTERVAL[0]])
        self.assertEqual(duplicate['duplicate_findings'],1)
        self.assertFalse(duplicate['checks']['valid_counterexamples'])
        invalid=copy.deepcopy(INTERVAL);invalid[0]['args']['point']=2
        score=grading.grade(case,invalid)
        self.assertEqual(score['invalid_witnesses'],1);self.assertEqual(score['missed_defects'],1)

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_domain_bounds_and_bool_do_not_count_as_counterexamples(self):
        case=grading.cases()[0]
        for args in ({'count':True,'size':3},{'count':0,'size':0},{'count':101,'size':1},
                     {'count':0,'size':1,'unexpected':0}):
            score=grading.grade(case,[{'function':'F','args':args}])
            self.assertEqual(score['verified_defects'],0);self.assertEqual(score['invalid_witnesses'],1)

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_unsubmitted_and_foreign_case_do_not_pass(self):
        case=grading.cases()[0]
        self.assertFalse(grading.grade(case,None)['checks']['submission_contract'])
        with self.assertRaises(ValueError):grading.grade(dict(case,id='foreign'),INTERVAL)

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_read_only_receipt_has_no_grader_feedback_or_archived_findings(self):
        case=grading.cases()[0];original=copy.deepcopy(case);owned=grading.Workspace(case)
        try:
            for name in case['files']:self.assertTrue(owned.handle('trial_read',{'path':name})[0])
            self.assertFalse(owned.handle('trial_read',{'path':'../review_worker.py'})[0])
            self.assertFalse(owned.handle('trial_write',{'path':'windows.py','source':'bad'})[0])
            accepted,receipt=owned.handle('trial_submit_findings',{'findings':INTERVAL})
            self.assertTrue(accepted);self.assertEqual(receipt,{'received':True})
            self.assertFalse(owned.handle('trial_submit_findings',{'findings':[]})[0])
            report=owned.report()
            self.assertTrue(report['workflow_complete']);self.assertTrue(report['fixture_unchanged'])
            self.assertFalse(report['harness_invalid']);self.assertFalse(report['finding_payloads_saved'])
            self.assertNotIn('args',json.dumps(report));self.assertNotIn('intervals',json.dumps(report))
            self.assertEqual(set(report['review_score']),grading.COUNTERS)
            self.assertEqual(sorted(p.name for p in owned.root.iterdir()),sorted(case['files']))
        finally:path=owned.root;owned.close()
        self.assertFalse(path.exists());self.assertIsNone(owned.findings);self.assertEqual(case,original)

    def test_unexpected_counterexample_is_harness_error_not_model_false_positive(self):
        owned=grading.Workspace(grading.cases()[0])
        try:
            with patch('tests.review_trials.grade',return_value={'checks':{'oracle_consistent':False},
                                                               'unexpected_counterexamples':1}):
                self.assertTrue(owned.report()['harness_invalid'])
        finally:owned.close()


class ReviewRunnerTests(unittest.TestCase):
    def test_case_selection_preserves_original_rotation_and_rejects_unknown(self):
        whole=design_trials()
        self.assertEqual(design_trials('ordered-review'),whole[3:])
        self.assertEqual([s['requested_model'] for s in design_trials('ordered-review')],
                         ['gpt-6.1-sol','gpt-6-astra','gpt-6-luna'])
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_review_trials.sandbox_controls') as controls,patch('tests.run_review_trials.run_arm') as arm:
            output=Path(tmp)/'new'
            with self.assertRaises(ValueError):run_trials(output,3,'unknown')
            self.assertFalse(output.exists());controls.assert_not_called();arm.assert_not_called()

    def test_selected_case_intent_precedes_call_and_completes_only_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new'
            def arm(case,model,**kwargs):
                r=json.loads((output/'report.json').read_text())
                self.assertEqual(r['case_filter'],'ordered-review')
                self.assertEqual(r['planned_turns'],design_trials('ordered-review'))
                self.assertEqual(r['attempts'][-1]['status'],'intent')
                self.assertEqual(case['id'],'ordered-review')
                return {'status':'finished','terminal':'completed','quality_admissible':True,
                        'inference_requests':1,'output_check':True}
            with patch('tests.run_review_trials.run_arm',side_effect=arm) as call,patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                r=run_trials(output,3,'ordered-review')
            self.assertEqual(call.call_count,3);self.assertEqual(r['passed'],3)
            self.assertTrue(r['complete_selected_design']);self.assertFalse(r['complete_design'])

    def test_selected_partial_budget_is_not_complete(self):
        sample={'status':'finished','terminal':'completed','quality_admissible':True,'inference_requests':1,'output_check':True}
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_review_trials.run_arm',return_value=sample) as call,patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new',1,'ordered-review')
        self.assertEqual(call.call_count,1);self.assertFalse(r['complete_selected_design'])
        self.assertFalse(r['complete_design']);self.assertEqual(len(r['planned_turns']),3)

    def test_frozen_intents_precede_each_call_and_only_review_tools_are_exposed(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new'
            def arm(case,model,effort,workspace,dynamic_specs,task_kind):
                report=json.loads((output/'report.json').read_text())
                self.assertEqual(report['attempts'][-1]['status'],'intent')
                self.assertEqual(len(report['planned_turns']),6)
                self.assertEqual(effort,'high');self.assertEqual(task_kind,'review')
                self.assertEqual({t['name'] for t in dynamic_specs[0]['tools']},
                                 {'trial_read','trial_submit_findings'})
                calls.append((case['id'],model))
                return {'status':'finished','terminal':'completed','quality_admissible':True,
                        'inference_requests':1,'output_check':True}
            with patch('tests.run_review_trials.run_arm',side_effect=arm),patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                report=run_trials(output)
            self.assertEqual(report['native_turn_requests'],6);self.assertEqual(report['passed'],6)
            self.assertTrue(report['complete_design']);self.assertFalse(report['policy_activation_eligible'])
            self.assertEqual(calls[0][1],'gpt-6-luna');self.assertEqual(calls[3][1],'gpt-6.1-sol')
            with patch('tests.run_review_trials.sandbox_controls',return_value={}),self.assertRaises(FileExistsError):run_trials(output)

    def test_quality_failure_continues_but_oracle_failure_stops_and_is_excluded(self):
        sample={'status':'finished','terminal':'completed','quality_admissible':True,'inference_requests':1}
        results=[dict(sample,output_check=False),dict(sample,output_check=True,harness_invalid=True)]
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_review_trials.run_arm',side_effect=results) as call,patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            report=run_trials(Path(tmp)/'new')
        self.assertEqual(call.call_count,2);self.assertEqual(report['quality_attempts'],1)
        self.assertEqual(report['passed'],0);self.assertTrue(report['campaign_stopped'])
        self.assertFalse(report['attempts'][1]['quality_admissible'])

    def test_interruption_and_bounds_preserve_unknown_consumption(self):
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_review_trials.run_arm',side_effect=KeyboardInterrupt),patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            report=run_trials(Path(tmp)/'new')
        self.assertEqual(report['native_turn_requests'],1);self.assertTrue(report['campaign_stopped'])
        self.assertEqual(report['attempts'][0]['status'],'interrupted')
        for count in (0,7,True):
            with self.assertRaises(ValueError):run_trials(Path('unused'),count)

    def test_partial_campaign_does_not_claim_complete_comparison(self):
        sample={'status':'finished','terminal':'completed','quality_admissible':True,'inference_requests':1,'output_check':True}
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_review_trials.run_arm',return_value=sample) as call,patch('tests.run_review_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            report=run_trials(Path(tmp)/'new',1)
        self.assertEqual(call.call_count,1);self.assertFalse(report['complete_design'])


if __name__=='__main__':unittest.main()
