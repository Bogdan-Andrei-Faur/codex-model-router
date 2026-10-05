import json
from pathlib import Path
import queue
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests import multifile_trials as grading
from tests.run_multifile_trials import RawEvidence, TrialClient, run_trials, isolated_overrides
from tests.probe_dynamic_tools import EchoWorkspace, probe
from tests.evaluate_jev_trials import aggregate, safe_result, scenarios, evaluate, link_measured, validate_native
from tests.test_coding_trials import TRANSITION_REFERENCE

USAGE={
    'snapshots.py':'''def delta(before,after):
    fields=('inputTokens','outputTokens','cachedInputTokens')
    for snapshot in (before,after):
        if not isinstance(snapshot,dict) or any(type(snapshot.get(k)) is not int or snapshot[k]<0 for k in fields):return None
        if snapshot['cachedInputTokens']>snapshot['inputTokens']:return None
    result={k:after[k]-before[k] for k in fields}
    return result if all(v>=0 for v in result.values()) else None
''',
    'session.py':'''from snapshots import delta
def aggregate(attempts):
    totals={'inputTokens':0,'outputTokens':0,'cachedInputTokens':0}
    complete=bool(attempts)
    for attempt in attempts:
        change=delta(attempt['before'],attempt['after'])
        if change is None:complete=False
        else:
            for key in totals:totals[key]+=change[key]
    return {'attempts':len(attempts),'coverage_complete':complete,'tokens':totals if complete else None}
'''}
TRANSITION={'policy.py':TRANSITION_REFERENCE.replace('def transition(','def plan('),
    'executor.py':'''from policy import plan
def apply_request(state,target,effort,catalog):
    decision=plan(state['model'],target,effort,state['active_turn'],catalog)
    result=dict(state)
    if decision['action']=='apply':result.update(model=target,effort=effort)
    return {'state':result,'decision':decision}
'''}


class MultifileTests(unittest.TestCase):
    def test_code_mode_only_profile_retains_executor_and_disables_unrelated_tools(self):
        with patch('tests.native_probe_profile.Path.exists',return_value=False):overrides=isolated_overrides()
        self.assertTrue(overrides['features.code_mode']);self.assertTrue(overrides['features.code_mode_host'])
        for key in ('features.shell_tool','features.unified_exec','features.apps','features.plugins','features.multi_agent','features.memories'):
            self.assertIs(overrides[key],False)
        self.assertEqual(overrides['web_search'],'disabled')

    def test_echo_requires_actual_valid_call_and_persists_intent_before_native_call(self):
        workspace=EchoWorkspace()
        try:
            self.assertFalse(workspace.report()['checks']['echo_roundtrip'])
            self.assertFalse(workspace.handle('trial_echo',{'value':True})[0])
            self.assertTrue(workspace.handle('trial_echo',{'value':37})[0])
            self.assertTrue(workspace.report()['checks']['echo_roundtrip'])
            workspace.handle('private-unplanned-tool',{})
            self.assertNotIn('private-unplanned-tool',json.dumps(workspace.report()))
            self.assertFalse(workspace.handle('trial_echo',{'value':37})[0])
        finally:workspace.close()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new'
            def fake(*args,**kwargs):
                self.assertEqual(json.loads((output/'report.json').read_text())['attempts'][0]['status'],'intent')
                kwargs['workspace'].close();return {'status':'finished','output_check':False}
            with patch('tests.probe_dynamic_tools.run_arm',side_effect=fake) as call:report=probe(output)
            self.assertEqual(call.call_count,1);self.assertEqual(report['max_turns'],1)
            self.assertFalse(report['attempts'][0]['output_check'])

    def test_frozen_rubric_and_import_boundary(self):
        self.assertEqual(len(grading.cases()),2)
        spec=grading.tools()[0]
        self.assertEqual(spec['type'],'namespace');self.assertEqual(spec['name'],'trial')
        for tool in spec['tools']:
            self.assertEqual(tool['type'],'function');self.assertIs(tool['deferLoading'],False)
        self.assertTrue(grading.module_contract(USAGE['session.py'],{'session','snapshots'}))
        for source in ('import os\ndef f():return 1','from pathlib import Path\ndef f():return 1',
                       'from .snapshots import delta\ndef f():return 1','def f():return (1).__class__',
                       'def f():return open("secret")','import snapshots as __x\ndef f():return 1'):
            self.assertFalse(grading.module_contract(source,{'snapshots'}))

    @unittest.skipUnless(sys.platform=='darwin','Requires native Seatbelt')
    def test_independent_grader_detects_both_original_bugs_and_reference_passes(self):
        for case,reference in zip(grading.cases(),(USAGE,TRANSITION)):
            self.assertTrue(all(grading.grade(case,reference).values()))
            self.assertFalse(all(grading.grade(case,case['files']).values()))

    @unittest.skipUnless(sys.platform=='darwin','Requires native Seatbelt')
    def test_host_allowlist_revision_and_tool_budget(self):
        workspace=grading.Workspace(grading.cases()[0])
        try:
            self.assertFalse(workspace.handle('trial_read',{'path':'../secret'})[0])
            self.assertFalse(workspace.handle('arbitrary-private-tool',{})[0])
            for name,source in USAGE.items():
                self.assertTrue(workspace.handle('trial_read',{'path':name})[0])
                self.assertTrue(workspace.handle('trial_write',{'path':name,'source':source})[0])
            self.assertTrue(workspace.handle('trial_test',{})[1]['passed'])
            self.assertTrue(workspace.report()['successful_test_on_final_revision'])
            workspace.handle('trial_write',{'path':'session.py','source':USAGE['session.py']})
            self.assertFalse(workspace.report()['successful_test_on_final_revision'])
            for _ in range(41):workspace.handle('trial_read',{'path':'session.py'})
            self.assertFalse(workspace.handle('trial_test',{})[0])
            self.assertNotIn('arbitrary-private-tool',json.dumps(workspace.report()))
        finally:workspace.close()

    def test_raw_ids_must_join_schema_fields_and_duplicates_never_sum(self):
        observer=RawEvidence();observer.thread='thread-private';observer.turn='turn-private'
        usage=dict(inputTokens=10,cachedInputTokens=2,outputTokens=4,reasoningOutputTokens=3,totalTokens=14)
        params={'responseId':'response-private','threadId':observer.thread,'turnId':observer.turn,'usage':usage,
                'usageMetadata':{'amount':'secret-amount','metadata':{'private_key':'secret-payload','model':'gpt-6-astra'}}}
        event={'method':'rawResponse/completed','params':params}
        observer.consume(event);observer.consume(event)
        observer.consume({'method':'rawResponse/completed','params':dict(params,turnId='other-turn')})
        report=observer.report();encoded=json.dumps(report)
        self.assertEqual(report['counts'],{'joined':1,'duplicates':1,'unjoined':1})
        self.assertEqual(report['response_tokens_sum']['inputTokens'],10)
        self.assertEqual(report['model_linked_responses'],0)
        for secret in ('thread-private','turn-private','response-private','secret','private_key','gpt-6-astra'):
            self.assertNotIn(secret,encoded)
        self.assertEqual(report['complete_inference_cost_coverage'],'unknown')

    def test_snake_case_or_missing_response_ids_cannot_fake_join(self):
        observer=RawEvidence();observer.thread='T';observer.turn='U'
        observer.consume({'method':'codex/event/raw_response_completed','params':{'msg':{'type':'raw_response_completed',
            'thread_id':'T','turn_id':'U','response_id':'R'}}})
        self.assertEqual(observer.report()['counts'],{'unjoined':1})

    def test_invalid_usage_is_unknown_and_cannot_be_counted_as_full_coverage(self):
        observer=RawEvidence();observer.thread='T';observer.turn='U'
        observer.consume({'method':'rawResponse/completed','params':{'responseId':'R','threadId':'T','turnId':'U',
            'usage':dict(inputTokens=10,cachedInputTokens=11,outputTokens=4,reasoningOutputTokens=3,totalTokens=14)}})
        self.assertEqual(observer.report()['responses_missing_usage'],1)
        self.assertIsNone(observer.report()['response_tokens_sum'])

    def test_tool_roundtrip_only_accepts_own_namespace_thread_turn_and_never_approvals(self):
        from tests.probe_inference_identity import IdentityShapes
        client=object.__new__(TrialClient);client.messages=queue.Queue();client.shapes=IdentityShapes()
        client.shapes.native_thread='T';client.shapes.native_turn='U';client.raw=RawEvidence()
        client.workspace=unittest.mock.Mock();client.workspace.handle.return_value=(True,{'passed':True})
        client.turn_finished=False;client.items={};client.denied_requests=0;sent=[];client.send=sent.append
        params={'threadId':'T','turnId':'U','namespace':'trial','tool':'trial_test','arguments':{},'callId':'C'}
        client.messages.put({'id':1,'method':'item/tool/call','params':params});client.next()
        self.assertTrue(sent[-1]['result']['success']);self.assertEqual(client.workspace.handle.call_count,1)
        for change in ({'turnId':'other'},{'namespace':'other'}):
            client.messages.put({'id':2,'method':'item/tool/call','params':dict(params,**change)});client.next()
            self.assertIn('error',sent[-1])
        client.messages.put({'id':3,'method':'item/commandExecution/requestApproval','params':params});client.next()
        self.assertIn('error',sent[-1]);self.assertEqual(client.denied_requests,3)
        self.assertEqual(client.workspace.handle.call_count,1)

    def test_runner_persists_intent_before_every_call_and_retains_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report'
            def fake(case,model):
                intent=json.loads((output/'report.json').read_text())['attempts'][-1]
                self.assertEqual(intent['status'],'intent')
                if model=='gpt-6-luna':raise RuntimeError('private-error')
                return {'status':'finished','output_check':True}
            with patch('tests.run_multifile_trials.run_arm',side_effect=fake),patch('tests.run_multifile_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                report=run_trials(output)
            self.assertEqual(len(report['attempts']),6);self.assertEqual(report['passed'],4)
            self.assertFalse(report['complete_design']);self.assertFalse(report['policy_activation_eligible'])
            self.assertNotIn('private-error',(output/'report.json').read_text())
            if sys.platform!='win32':
                self.assertEqual((output/'report.json').stat().st_mode & 0o777,0o600)

    def test_prior_preflight_failures_retained_and_total_inference_bound_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'prior.json';prior={'schema':'isolated-multifile-trials/1','case_sha256':grading.CASE_HASH,
                'grader_sha256':grading.GRADER_HASH,'attempts':[{'inference_requests':1}]*3+[{'inference_requests':0}]*3}
            p.write_text(json.dumps(prior))
            with patch('tests.run_multifile_trials.run_arm',return_value={'status':'finished','inference_requests':1,'quality_admissible':True,'output_check':True}),patch('tests.run_multifile_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                report=run_trials(Path(tmp)/'new',3,p,'transition-integration')
            self.assertEqual(len(report['attempts']),9);self.assertEqual(report['native_turn_requests'],6)
            self.assertTrue(report['completed_primary_design']);self.assertFalse(report['complete_design'])
            with self.assertRaises(ValueError):run_trials(Path(tmp)/'too_many',4,p,'transition-integration')

    def test_interrupted_native_attempt_stops_design_and_is_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_multifile_trials.run_arm',return_value={
            'status':'interrupted','interrupted':True,'inference_requests':1,'output_check':False}) as call,patch('tests.run_multifile_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            report=run_trials(Path(tmp)/'new')
        self.assertEqual(call.call_count,1);self.assertEqual(report['native_turn_requests'],1)
        self.assertEqual(report['attempts'][0]['status'],'interrupted')
        self.assertFalse(report['tool_availability_verified']);self.assertIsNone(report['quality_pass_rate'])


class JevTrialTests(unittest.TestCase):
    def execution(self,scenario,passed=True):
        return {'case_id':scenario['id'],'requested_model':'gpt-6.1-sol','requested_effort':'high',
            'terminal':'completed','status':'finished','attempt':1,'inference_requests':1,
            'denied_native_requests':0,'native_catalog':{'gpt-6.1-sol':['high']},
            'posterior_model_log_records':{'gpt-6.1-sol':1},'quality_admissible':True,
            'checks':{'external_integration':passed},'workflow_complete':passed,'output_check':passed}

    def test_existing_calls_can_be_linked_offline_without_changing_confidence_or_labels(self):
        scenario=scenarios()[3];route={'model':'gpt-6.1-sol','effort':'high'}
        row=safe_result({'status':'ok','route':route,'confidence':.35},scenario,{'route':route},[])
        row['case_id']=scenario['id'];report={'schema':'jev-descriptive-trials/1','case_sha256':grading.CASE_HASH,'attempts':[row]}
        native={'schema':'isolated-multifile-trials/1','case_sha256':grading.CASE_HASH,
            'grader_sha256':grading.GRADER_HASH,'attempts':[self.execution(scenario)]}
        linked=link_measured(report,native)
        self.assertIs(linked['attempts'][0]['measured_exercise_pass'],True)
        self.assertEqual(linked['attempts'][0]['confidence'],.35);self.assertEqual(linked['measurement_link_provider_calls'],0)
        self.assertIsNone(report['attempts'][0]['measured_exercise_pass'])
        self.assertIsNone(linked['summary']['calibrated_threshold'])
    def test_quality_needs_matching_actual_exercise_model_and_requested_effort(self):
        scenario=scenarios()[2];route={'model':'gpt-6.1-sol','effort':'high'};choices={'choice':route}
        measured=[self.execution(scenario,False)]
        row=safe_result({'status':'ok','route':route,'confidence':.9345},scenario,choices,measured)
        self.assertIs(row['measured_exercise_pass'],False);self.assertEqual(row['confidence'],.9345)
        self.assertFalse(row['independent_model_judgment_possible'])
        measured[0]['requested_effort']='medium'
        self.assertIsNone(safe_result({'status':'ok','route':route},scenario,choices,measured)['measured_exercise_pass'])

    def test_duplicate_and_failed_retry_cannot_be_hidden_by_first_match(self):
        scenario=scenarios()[2];route={'model':'gpt-6.1-sol','effort':'high'}
        for outcomes in ((True,False),(False,True),(True,True)):
            with self.subTest(outcomes=outcomes):
                measured=[self.execution(scenario,p) for p in outcomes];measured[1]['attempt']=2
                row=safe_result({'status':'ok','route':route},scenario,{'route':route},measured)
                self.assertIsNone(row['measured_exercise_pass'])
                self.assertEqual(row['measurement_reason'],'ambiguous_execution_sequence')
                self.assertEqual(row['matching_execution_attempts'],2)
                self.assertEqual(row['observed_failed_checks'],sum(not p for p in outcomes))
        measured=[self.execution(scenario),{'case_id':scenario['id'],'requested_model':route['model'],
            'requested_effort':'high','status':'intent'}]
        self.assertIsNone(safe_result({'status':'ok','route':route},scenario,{'route':route},measured)['measured_exercise_pass'])

    def test_incomplete_or_inconsistent_evidence_cannot_be_positive_quality(self):
        scenario=scenarios()[2];route={'model':'gpt-6.1-sol','effort':'high'}
        changes=[{'output_check':'true'},{'output_check':1},{'checks':{}},{'checks':{'x':'passed'}},
            {'workflow_complete':False},{'checks':{'x':False}},{'terminal':'failed'},
            {'failure':'native_failure'},{'denied_native_requests':1},{'inference_requests':True},
            {'attempt':2},{'native_catalog':{}},{'posterior_model_log_records':{route['model']:True}},
            {'posterior_model_log_records':{route['model']:1,'gpt-6-astra':1}}]
        for change in changes:
            with self.subTest(change=change):
                execution=self.execution(scenario);execution.update(change)
                row=safe_result({'status':'ok','route':route},scenario,{'route':route},[execution])
                self.assertIsNone(row['measured_exercise_pass'])

    def test_legacy_summary_malformed_costs_and_outcomes_stay_unknown(self):
        rows=[{'provider_reported_cost_usd':v,'measured_exercise_pass':'true'}
            for v in (True,float('nan'),float('inf'),-1,10001,'0.1')]
        rows.append({'provider_reported_cost_usd':.1,'measured_exercise_pass':False})
        summary=aggregate(rows)
        self.assertEqual(summary['known_provider_cost_usd'],.1)
        self.assertFalse(summary['provider_cost_coverage_complete'])
        self.assertEqual(summary['confidence_bins']['unknown']['measured_outcomes'],1)
        self.assertEqual(summary['confidence_bins']['unknown']['measured_passes'],0)

    def test_link_rejects_duplicate_classifier_cases_or_foreign_schema(self):
        scenario=scenarios()[2];route={'model':'gpt-6.1-sol','effort':'high'}
        row=safe_result({'status':'ok','route':route},scenario,{'route':route},[]);row['case_id']=scenario['id']
        report={'schema':'jev-descriptive-trials/1','case_sha256':grading.CASE_HASH,'attempts':[row,row]}
        native={'schema':'isolated-multifile-trials/1','case_sha256':grading.CASE_HASH,
            'grader_sha256':grading.GRADER_HASH,'attempts':[self.execution(scenario)]}
        with self.assertRaisesRegex(ValueError,'ambiguous_measurement_cohort'):link_measured(report,native)
        report['attempts']=[row];native['schema']='other'
        with self.assertRaisesRegex(ValueError,'measurement_rubric_mismatch'):link_measured(report,native)

    def test_invalid_classifier_selection_cannot_acquire_measured_outcome(self):
        scenario=scenarios()[2];route={'model':'gpt-6.1-sol','effort':'high'}
        row=safe_result({'status':'invalid','route':route},scenario,{'route':route},[self.execution(scenario)])
        self.assertIsNone(row['measured_exercise_pass']);self.assertFalse(row['valid_eligible_choice'])

    def test_native_origin_requires_frozen_grader_and_typed_attempts(self):
        for change in ({'case_sha256':'other'},{'grader_sha256':'other'},{'attempts':[None]}):
            native={'schema':'isolated-multifile-trials/1','case_sha256':grading.CASE_HASH,
                'grader_sha256':grading.GRADER_HASH,'attempts':[]};native.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):validate_native(native)

    def test_abstention_and_missing_cost_confidence_are_unknown_not_zero_or_calibrated(self):
        scenario=scenarios()[0];row=safe_result({'status':'abstained','confidence':True,'engine_provider_cost_usd':False,
            'private_payload':'secret'},scenario,{},[])
        self.assertIsNone(row['confidence']);self.assertIsNone(row['reviewed_scope_consistent'])
        summary=aggregate([row]);self.assertIsNone(summary['known_provider_cost_usd'])
        self.assertFalse(summary['provider_cost_coverage_complete']);self.assertFalse(summary['statistically_calibrated'])
        self.assertIsNone(summary['calibrated_threshold']);self.assertNotIn('secret',json.dumps(row))

    def test_six_provider_calls_bound_and_no_health_write(self):
        with tempfile.TemporaryDirectory() as tmp,patch('tests.evaluate_jev_trials._run_jev',return_value={'status':'unavailable'}) as call,patch('builtins.print'):
            output=Path(tmp)/'output';catalog={m:['low','medium','high','xhigh'] for m in ('gpt-6-luna','gpt-6.1-sol','gpt-6-astra')}
            report=evaluate({},Path(tmp),catalog,output)
            self.assertEqual(call.call_count,6);self.assertEqual(len(report['attempts']),6)
            self.assertFalse(report['runtime_health_or_configuration_changed'])
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),['output'])


if __name__=='__main__':unittest.main()
