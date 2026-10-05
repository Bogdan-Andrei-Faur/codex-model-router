import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import integration_trials as grading
from tests.run_integration_trials import run_trials, design_trials

TELEMETRY={
    'records.py':'''def normalize(record,target):
    scope=('runtime','thread','turn')
    fields=('inputTokens','cachedInputTokens','outputTokens')
    if not isinstance(target,dict) or any(not isinstance(target.get(k),str) or not target[k] for k in scope):return None
    if not isinstance(record,dict) or any(record.get(k)!=target[k] for k in scope):return None
    if not isinstance(record.get('response_id'),str) or not record['response_id']:return None
    if record.get('model') not in ('gpt-6-luna','gpt-6.1-sol','gpt-6-astra'):return None
    tokens=record.get('tokens')
    if not isinstance(tokens,dict) or any(type(tokens.get(k)) is not int or tokens[k]<0 for k in fields):return None
    if tokens['cachedInputTokens']>tokens['inputTokens']:return None
    result={k:record[k] for k in scope}
    result.update(response_id=record['response_id'],model=record['model'],tokens={k:tokens[k] for k in fields})
    return result
''',
    'ledger.py':'''from records import normalize
def collect(records,target):
    kept={};conflicts=set()
    for raw in records:
        row=normalize(raw,target)
        if row is None:continue
        key=row['response_id']
        if key in conflicts:continue
        if key in kept and kept[key]!=row:
            conflicts.add(key)
            kept.pop(key)
        else:kept[key]=row
    return {'responses':[kept[k] for k in sorted(kept)],'conflicts':sorted(conflicts)}
''',
    'totals.py':'''from ledger import collect
def summarize(records,target):
    result=collect(records,target);rows=result['responses'];conflicts=result['conflicts']
    complete=bool(rows) and not conflicts
    tokens={k:sum(r['tokens'][k] for r in rows) for k in ('inputTokens','cachedInputTokens','outputTokens')} if complete else None
    return {'response_count':len(rows),'conflict_count':len(conflicts),'coverage_complete':complete,
        'tokens':tokens,'models':sorted({r['model'] for r in rows})}
'''}

CANCELLATION={
    'rules.py':'''def plan(state,event):
    if not isinstance(state.get('turn'),str) or not state['turn']:return 'ignore'
    if state.get('status') not in ('running','cancelling','cancelled','completed','failed'):return 'ignore'
    if type(state.get('cancel_requested')) is not bool:return 'ignore'
    if type(state.get('phase_requests')) is not int or state['phase_requests']<0:return 'ignore'
    if not isinstance(event,dict) or event.get('turn')!=state['turn']:return 'ignore'
    if state['status'] in ('cancelled','completed','failed'):return 'ignore'
    kind=event.get('kind')
    if kind in ('request_cancel','phase_request'):
        if state['status']!='running' or state['cancel_requested']:return 'ignore'
        return 'begin_cancel' if kind=='request_cancel' else 'allow_phase'
    return {'native_cancelled':'finish_cancel','native_completed':'finish_completed','native_failed':'finish_failed'}.get(kind,'ignore')
''',
    'executor.py':'''from rules import plan
def reduce_event(state,event):
    action=plan(state,event);result=dict(state)
    if action=='begin_cancel':result.update(status='cancelling',cancel_requested=True)
    elif action=='allow_phase':result['phase_requests']+=1
    elif action in ('finish_cancel','finish_completed','finish_failed'):
        result['status']={'finish_cancel':'cancelled','finish_completed':'completed','finish_failed':'failed'}[action]
    return result
''',
    'replay.py':'''from executor import reduce_event
def apply_events(state,events):
    result=dict(state)
    for event in events:result=reduce_event(result,event)
    return result
'''}


class IntegrationGraderTests(unittest.TestCase):
    def test_frozen_references_pass_and_seeds_fail(self):
        for case,reference in zip(grading.cases(),(TELEMETRY,CANCELLATION)):
            with self.subTest(case=case['id']):
                self.assertTrue(all(grading.grade(case,reference).values()))
                self.assertFalse(all(grading.grade(case,case['files']).values()))

    def test_telemetry_known_defects_are_detected(self):
        case=grading.cases()[0]
        mutants=[('records.py',"any(record.get(k)!=target[k] for k in scope)","False"),
            ('records.py',"type(tokens.get(k)) is not int","not isinstance(tokens.get(k),int)"),
            ('ledger.py',"if key in conflicts:continue","if False:continue"),
            ('ledger.py',"if key in kept and kept[key]!=row:","if False:"),
            ('totals.py',"complete=bool(rows) and not conflicts","complete=bool(rows)")]
        for name,old,new in mutants:
            source=dict(TELEMETRY);source[name]=source[name].replace(old,new)
            with self.subTest(defect=old):self.assertFalse(all(grading.grade(case,source).values()))

    def test_cancellation_known_ordering_defects_are_detected(self):
        case=grading.cases()[1]
        mutants=[('rules.py',"if state['status'] in ('cancelled','completed','failed'):return 'ignore'","if False:return 'ignore'"),
            ('rules.py',"if state['status']!='running' or state['cancel_requested']:return 'ignore'","if False:return 'ignore'"),
            ('executor.py',"status='cancelling'","status='cancelled'"),
            ('executor.py',"result=dict(state)","result=state"),
            ('replay.py',"result=dict(state)","result=state"),
            ('replay.py',"for event in events:","for event in events[::-1]:")]
        for name,old,new in mutants:
            source=dict(CANCELLATION);source[name]=source[name].replace(old,new)
            with self.subTest(defect=old):self.assertFalse(all(grading.grade(case,source).values()))

    def test_workspace_three_files_and_final_revision_checks(self):
        case=grading.cases()[0];original=copy.deepcopy(case)
        with tempfile.TemporaryDirectory() as parent:
            owned=grading.workspace(case)
            try:
                for name in case['files']:
                    self.assertTrue(owned.handle('trial_read',{'path':name})[0])
                    self.assertTrue(owned.handle('trial_write',{'path':name,'source':TELEMETRY[name]})[0])
                self.assertTrue(owned.handle('trial_test',{})[1]['passed'])
                self.assertTrue(owned.report()['workflow_complete'])
                owned.handle('trial_write',{'path':'totals.py','source':TELEMETRY['totals.py']})
                self.assertFalse(owned.report()['successful_test_on_final_revision'])
                self.assertFalse(owned.handle('trial_read',{'path':'../worker.py'})[0])
                self.assertFalse(owned.handle('trial_write',{'path':'records.py','source':'import os'})[0])
            finally:
                path=owned.root;owned.close()
            self.assertFalse(path.exists());self.assertEqual(case,original)

    def test_foreign_fixture_or_unsafe_source_cannot_be_graded(self):
        case=grading.cases()[0]
        with self.assertRaises(ValueError):grading.grade(dict(case,id='other'),TELEMETRY)
        source=dict(TELEMETRY);source['records.py']='import os\ndef normalize(record,target):\n    return None\n'
        self.assertEqual(grading.grade(case,source),{'source_contract':False})


class IntegrationRunnerTests(unittest.TestCase):
    def test_intent_precedes_calls_and_complete_design_rotates_model_order(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new'
            def arm(case,model,effort,workspace):
                self.assertEqual(effort,'high')
                report=json.loads((output/'report.json').read_text())
                self.assertEqual(report['attempts'][-1]['status'],'intent')
                calls.append((case['id'],model))
                workspace.close()
                return {'status':'finished','terminal':'completed','quality_admissible':True,
                    'inference_requests':1,'output_check':True}
            with patch('tests.run_integration_trials.run_arm',side_effect=arm),patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                report=run_trials(output)
            self.assertEqual(report['native_turn_requests'],6);self.assertEqual(report['passed'],6)
            self.assertTrue(report['complete_design']);self.assertFalse(report['policy_activation_eligible'])
            self.assertEqual(calls[0][1],'gpt-6-luna');self.assertEqual(calls[3][1],'gpt-6.1-sol')
            with self.assertRaises(FileExistsError):run_trials(output)

    def test_infrastructure_stops_and_quality_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            results=[{'status':'finished','terminal':'completed','quality_admissible':True,
                'inference_requests':1,'output_check':False},
                {'status':'finished','failure':'native_failure','inference_requests':1,'output_check':False}]
            with patch('tests.run_integration_trials.run_arm',side_effect=results) as call,patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                report=run_trials(Path(tmp)/'new')
            self.assertEqual(call.call_count,2);self.assertEqual(report['native_turn_requests'],2)
            self.assertEqual(report['quality_attempts'],1);self.assertEqual(report['quality_pass_rate'],0)
            self.assertTrue(report['campaign_stopped']);self.assertFalse(report['complete_design'])

    def test_interrupt_and_bounds_preserve_unknown_consumption(self):
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_integration_trials.run_arm',side_effect=KeyboardInterrupt),patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            report=run_trials(Path(tmp)/'new')
        self.assertEqual(report['native_turn_requests'],1);self.assertTrue(report['campaign_stopped'])
        self.assertEqual(report['attempts'][0]['status'],'interrupted')
        for value in (0,7,True):
            with self.assertRaises(ValueError):run_trials(Path('unused'),value)

    def test_effort_design_balances_two_independent_replicates_per_route(self):
        planned=design_trials('luna-high-sol-medium')
        self.assertEqual(len(planned),8)
        self.assertEqual(len({tuple(s[k] for k in ('case_id','requested_model','requested_effort','replicate')) for s in planned}),8)
        for n in (0,4):
            first=planned[n:n+2];second=planned[n+2:n+4]
            self.assertEqual([s['requested_model'] for s in first],list(reversed([s['requested_model'] for s in second])))
            self.assertEqual({(s['requested_model'],s['requested_effort']) for s in first},
                {('gpt-6-luna','high'),('gpt-6.1-sol','medium')})
        self.assertEqual([s['requested_model'] for s in planned[:2]],['gpt-6-luna','gpt-6.1-sol'])
        self.assertEqual([s['requested_model'] for s in planned[4:6]],['gpt-6.1-sol','gpt-6-luna'])

    def test_effort_plan_and_exact_request_are_persisted_before_every_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new';calls=[]
            def arm(case,model,effort,workspace):
                r=json.loads((output/'report.json').read_text());intent=r['attempts'][-1]
                self.assertEqual(r['planned_turns'],design_trials('luna-high-sol-medium'))
                self.assertEqual(intent['status'],'intent');self.assertEqual(intent['requested_effort'],effort)
                calls.append((case['id'],model,effort,intent['replicate']))
                return {'status':'finished','terminal':'completed','quality_admissible':True,
                    'inference_requests':1,'output_check':True}
            with patch('tests.run_integration_trials.run_arm',side_effect=arm),patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                r=run_trials(output,8,'luna-high-sol-medium')
        self.assertEqual(len(calls),8);self.assertEqual(r['native_turn_requests'],8)
        self.assertEqual(r['passed'],8);self.assertTrue(r['complete_design'])
        self.assertEqual(r['design'],'luna-high-sol-medium');self.assertEqual(len(r['design_sha256']),64)

    def test_partial_effort_design_never_claims_complete_comparison(self):
        sample={'status':'finished','terminal':'completed','quality_admissible':True,
            'inference_requests':1,'output_check':True}
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_integration_trials.run_arm',return_value=sample) as call,patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new',1,'luna-high-sol-medium')
        self.assertEqual(call.call_count,1);self.assertFalse(r['complete_design'])
        self.assertEqual(len(r['planned_turns']),8)
        with self.assertRaises(ValueError):run_trials(Path('unused'),9,'luna-high-sol-medium')
        with self.assertRaises(ValueError):design_trials('unknown')

    def test_workspace_cleanup_error_keeps_attempt_and_stops_budget(self):
        from unittest.mock import Mock
        owned=Mock();owned.close.side_effect=OSError('synthetic_cleanup_failure')
        sample={'status':'finished','terminal':'completed','quality_admissible':True,
            'inference_requests':1,'output_check':True}
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_integration_trials.grading.workspace',return_value=owned),patch('tests.run_integration_trials.run_arm',return_value=sample) as call,patch('tests.run_integration_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new',8,'luna-high-sol-medium')
        self.assertEqual(call.call_count,1);self.assertEqual(r['native_turn_requests'],1)
        self.assertEqual(r['attempts'][0]['cleanup_failure'],'owned_workspace_cleanup_failure')
        self.assertEqual(r['quality_attempts'],0);self.assertEqual(r['passed'],0)
        self.assertTrue(r['campaign_stopped']);self.assertFalse(r['complete_design'])


if __name__=='__main__':unittest.main()
