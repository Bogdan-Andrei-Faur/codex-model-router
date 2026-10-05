import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from tests import causal_trials as grading, trial_tool_evidence as tracing
from tests.test_causal_trials import REFERENCE
from tests.run_causal_tool_trials import run_trials


class ToolEvidenceTests(unittest.TestCase):
    def workspace(self,grade=None):
        return tracing.Workspace(grading.cases()[0],grade or grading.grade,grading.CHECKS)

    @unittest.skipUnless(sys.platform=='darwin','Requires native macOS Seatbelt grader')
    def test_failed_seed_then_repaired_test_links_revision_and_keeps_receipts(self):
        owned=self.workspace()
        try:
            for file in owned.case['files']:owned.handle('trial_read',{'path':file})
            success,result=owned.handle('trial_test',{})
            self.assertTrue(success);self.assertFalse(result['passed'])
            for file,source in REFERENCE.items():owned.handle('trial_write',{'path':file,'source':source})
            success,result=owned.handle('trial_test',{})
            self.assertTrue(success);self.assertTrue(result['passed'])
            report=owned.report();tests=[e for e in report['tool_events'] if e['tool']=='trial_test']
            self.assertEqual([e['passed'] for e in tests],[False,True])
            self.assertEqual([e['revision_before'] for e in tests],[0,4])
            self.assertTrue(all(e['evaluation_available'] for e in tests))
            self.assertTrue(report['workflow_complete']);self.assertFalse(report['harness_invalid'])
            self.assertEqual([e['sequence'] for e in report['tool_events']],list(range(1,11)))
            self.assertFalse(report['tool_payloads_saved'])
            owned.handle('trial_write',{'path':'graph.py','source':REFERENCE['graph.py']})
            self.assertFalse(owned.report()['successful_test_on_final_revision'])
            # A report is detached; consumers cannot change the live evidence.
            report['tool_events'].clear();self.assertEqual(len(owned.events),11)
        finally:path=owned.root;owned.close()
        self.assertFalse(path.exists())

    def test_fixed_rejection_categories_never_retain_payloads(self):
        owned=self.workspace();marker='private-marker-do-not-save'
        try:
            requests=[('trial_read',None,'invalid_arguments'),
                ('trial_read',{'path':[marker]},'invalid_arguments'),
                ('trial_read',{'path':'../'+marker},'path_not_allowed'),
                (marker,{},'unsupported_tool'),
                ('trial_write',{'path':'graph.py','source':'import os\n# '+marker},'source_contract'),
                ('trial_write',{'path':'graph.py','source':'\ud800'},'source_contract')]
            for tool,args,reason in requests:
                self.assertEqual(owned.handle(tool,args),(False,{'rejected':True}))
                self.assertEqual(owned.events[-1]['rejection_category'],reason)
            encoded=json.dumps(owned.report())
            self.assertNotIn(marker,encoded);self.assertNotIn('graph.py',encoded)
            self.assertFalse(any('source' in event for event in owned.events));self.assertEqual(owned.revision,0)
            self.assertEqual(set(owned.rejection_categories),{'invalid_arguments','path_not_allowed','unsupported_tool','source_contract'})
        finally:owned.close()

    def test_unsafe_owned_file_and_filesystem_errors_are_categorized(self):
        owned=self.workspace()
        try:
            path=owned.root/'graph.py';path.unlink();path.symlink_to(owned.root/'canonical.py')
            self.assertFalse(owned.handle('trial_read',{'path':'graph.py'})[0])
            self.assertEqual(owned.events[-1]['rejection_category'],'unsafe_file')
            with patch.object(Path,'read_text',side_effect=OSError('private-error')):
                self.assertFalse(owned.handle('trial_read',{'path':'canonical.py'})[0])
            self.assertEqual(owned.events[-1]['rejection_category'],'filesystem_error')
            self.assertNotIn('private-error',json.dumps(owned.events))
        finally:owned.close()

    def test_malformed_grader_result_is_unknown_not_passing_and_does_not_leak(self):
        complete={k:True for k in grading.CHECKS if k!='execution'}
        for bad in ({'private-marker':True},dict(complete,no_mutation='private-marker'),{},
                    {'source_contract':True},{'source_contract':True,'execution':False}):
            owned=self.workspace(lambda *_:bad)
            try:
                success,result=owned.handle('trial_test',{})
                self.assertTrue(success);self.assertFalse(result['passed'])
                self.assertFalse(owned.events[-1]['evaluation_available'])
                report=owned.report();self.assertTrue(report['harness_invalid'])
                self.assertNotIn('private-marker',json.dumps(report))
            finally:owned.close()

    def test_grader_exception_is_fixed_category_with_no_message(self):
        def fail(*_):raise RuntimeError('private-marker')
        owned=self.workspace(fail)
        try:
            self.assertFalse(owned.handle('trial_test',{})[1]['passed'])
            report=owned.report();self.assertTrue(report['harness_invalid'])
            self.assertEqual(set(report['grader_error_categories']),{'grader_exception'})
            self.assertNotIn('private-marker',json.dumps(report))
        finally:owned.close()

    def test_call_limit_bounds_trace_and_reports_missing_evidence(self):
        owned=self.workspace()
        try:
            for _ in range(42):owned.handle('trial_read',{'path':'graph.py'})
            report=owned.report();self.assertEqual(len(report['tool_events']),40)
            self.assertEqual(report['tool_events_dropped'],2);self.assertFalse(report['tool_trace_complete'])
            self.assertEqual(report['rejection_categories'],{'call_limit':2})
            self.assertEqual(report['tool_calls'],{'trial_read':42})
        finally:owned.close()


class ToolObservationRunnerTests(unittest.TestCase):
    def test_prospective_single_intent_and_hashes_precede_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new'
            def arm(case,model,effort,workspace,dynamic_specs):
                r=json.loads((output/'report.json').read_text())
                self.assertEqual(len(r['planned_turns']),1);self.assertEqual(r['attempts'][-1]['status'],'intent')
                self.assertEqual(len(r['tool_evidence_sha256']),64)
                self.assertEqual(model,'gpt-6-luna');self.assertEqual(effort,'high')
                self.assertIsInstance(workspace,tracing.Workspace)
                return {'terminal':'completed','quality_admissible':True,'inference_requests':1,
                        'output_check':True,'tool_trace_complete':True}
            with patch('tests.run_causal_tool_trials.run_arm',side_effect=arm) as call,patch('tests.run_causal_tool_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                r=run_trials(output)
        self.assertEqual(call.call_count,1);self.assertEqual(r['native_turn_requests'],1)
        self.assertTrue(r['complete_design']);self.assertFalse(r['policy_activation_eligible'])

    def test_incomplete_trace_or_bad_grader_excludes_quality_without_losing_attempt(self):
        sample={'terminal':'completed','quality_admissible':True,'inference_requests':1,'output_check':True}
        for extra in ({'tool_trace_complete':False},{'tool_trace_complete':True,'harness_invalid':True}):
            with tempfile.TemporaryDirectory() as tmp,patch('tests.run_causal_tool_trials.run_arm',return_value=dict(sample,**extra)),patch('tests.run_causal_tool_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                r=run_trials(Path(tmp)/'new')
            self.assertTrue(r['campaign_stopped']);self.assertEqual(r['quality_attempts'],0)
            self.assertEqual(r['native_turn_requests'],1)
        for v in (0,2,True):
            with self.assertRaises(ValueError):run_trials(Path('unused'),v)


if __name__=='__main__':unittest.main()
