from tests.grader_sandbox import INTEGRATION
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from tests import causal_trials as grading
from tests.run_causal_trials import run_trials

REFERENCE={
'canonical.py':'''def normalize(row):
    if not isinstance(row,dict) or set(row)!={'id','deps','kind','source','target','amount'}:return None
    if row['id'] not in ('a','b','c','d','e','f') or row['target'] not in ('A','B','C'):return None
    if type(row['amount']) is not int or not 1<=row['amount']<=9:return None
    if not isinstance(row['deps'],list) or len(row['deps'])>6 or any(d not in ('a','b','c','d','e','f') for d in row['deps']):return None
    if row['kind']=='credit':
        if row['source'] is not None:return None
    elif row['kind']=='transfer':
        if row['source'] not in ('A','B','C') or row['source']==row['target']:return None
    else:return None
    result=dict(row);result['deps']=sorted(set(row['deps']));return result

def collect(records):
    events={};conflicts=set()
    for raw in records:
        row=normalize(raw)
        if row is None:continue
        key=row['id']
        if key in conflicts:continue
        if key in events and events[key]!=row:
            conflicts.add(key);events.pop(key)
        else:events[key]=row
    return {'events':events,'conflicts':sorted(conflicts)}
''',
'graph.py':'''def order(events):
    remaining=set(events);done=[]
    while remaining:
        ready=sorted(k for k in remaining if all(d in done for d in events[k]['deps']))
        if not ready:break
        key=ready[0];remaining.remove(key);done.append(key)
    return {'order':done,'blocked':sorted(remaining)}
''',
'operations.py':'''def apply(stock,event):
    result=dict(stock)
    if event['kind']=='transfer':
        if result[event['source']]<event['amount']:return {'stock':result,'accepted':False}
        result[event['source']]-=event['amount']
    result[event['target']]+=event['amount']
    return {'stock':result,'accepted':True}
''',
'replay.py':'''from canonical import collect
from graph import order
from operations import apply
def run(stock,records):
    data=collect(records);schedule=order(data['events'])
    result={'stock':dict(stock),'applied':[],'rejected':[],'blocked':list(schedule['blocked']),'conflicts':list(data['conflicts'])}
    for key in schedule['order']:
        row=data['events'][key]
        if any(d not in result['applied'] for d in row['deps']):result['blocked'].append(key);continue
        step=apply(result['stock'],row);result['stock']=step['stock']
        result['applied' if step['accepted'] else 'rejected'].append(key)
    result['blocked']=sorted(result['blocked'])
    return result
'''}


class CausalGraderTests(unittest.TestCase):
    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_reference_passes_all_categories_and_seed_fails(self):
        case=grading.cases()[0]
        self.assertTrue(all(grading.grade(case,REFERENCE).values()))
        self.assertFalse(all(grading.grade(case,case['files']).values()))

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_cross_module_defects_are_detected(self):
        case=grading.cases()[0]
        mutants=[('canonical.py',"type(row['amount']) is not int","not isinstance(row['amount'],int)"),
            ('canonical.py',"sorted(set(row['deps']))","list(row['deps'])"),
            ('canonical.py',"if key in conflicts:continue","if False:continue"),
            ('canonical.py',"if key in events and events[key]!=row:","if False:"),
            ('graph.py',"all(d in done for d in events[k]['deps'])","all(d in events for d in events[k]['deps'])"),
            ('graph.py',"key=ready[0]","key=ready[-1]"),
            ('operations.py',"result=dict(stock)","result=stock"),
            ('operations.py',"return {'stock':result,'accepted':False}","return {'stock':dict(result,A=result['A']-event['amount']),'accepted':False}"),
            ('operations.py',"result[event['source']]<event['amount']","result[event['source']]<=event['amount']"),
            ('replay.py',"if any(d not in result['applied'] for d in row['deps']):","if False:"),
            ('replay.py',"'applied' if step['accepted'] else 'rejected'","'applied'"),
            ('replay.py',"result['blocked']=sorted(result['blocked'])","result['blocked']=sorted(result['blocked']+result['conflicts'])")]
        for file,old,new in mutants:
            with self.subTest(defect=old):
                self.assertIn(old,REFERENCE[file])
                source=dict(REFERENCE);source[file]=source[file].replace(old,new)
                self.assertFalse(all(grading.grade(case,source).values()))

    def test_foreign_case_and_unsafe_import_do_not_execute(self):
        case=grading.cases()[0]
        with self.assertRaises(ValueError):grading.grade(dict(case,id='other'),REFERENCE)
        source=dict(REFERENCE);source['graph.py']='import os\ndef order(events):return {}\n'
        self.assertEqual(grading.grade(case,source),{'source_contract':False})

    @unittest.skipUnless(INTEGRATION, 'Set ROUTER_TEST_DOCKER_GRADERS=1 with the pinned image')
    def test_four_files_final_revision_and_tool_paths(self):
        case=grading.cases()[0];owned=grading.workspace(case)
        try:
            for file in case['files']:
                self.assertIn(file,case['request'])
                self.assertTrue(owned.handle('trial_read',{'path':file})[0])
                self.assertTrue(owned.handle('trial_write',{'path':file,'source':REFERENCE[file]})[0])
            self.assertTrue(owned.handle('trial_test',{})[1]['passed'])
            self.assertTrue(owned.report()['workflow_complete'])
            owned.handle('trial_write',{'path':'graph.py','source':REFERENCE['graph.py']})
            self.assertFalse(owned.report()['successful_test_on_final_revision'])
            self.assertFalse(owned.handle('trial_read',{'path':'../worker.py'})[0])
            for tool in grading.tools(case)[0]['tools']:
                if 'path' in tool['inputSchema']['properties']:
                    self.assertEqual(set(tool['inputSchema']['properties']['path']['enum']),set(case['files']))
        finally:path=owned.root;owned.close()
        self.assertFalse(path.exists())


class CausalRunnerTests(unittest.TestCase):
    def test_intents_and_frozen_three_member_plan_precede_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'new';calls=[]
            def arm(case,model,effort,workspace,dynamic_specs):
                r=json.loads((output/'report.json').read_text())
                self.assertEqual(len(r['planned_turns']),3);self.assertEqual(r['attempts'][-1]['status'],'intent')
                self.assertEqual(effort,'high');self.assertEqual(len(case['files']),4)
                calls.append(model)
                return {'status':'finished','terminal':'completed','quality_admissible':True,'inference_requests':1,'output_check':True}
            with patch('tests.run_causal_trials.run_arm',side_effect=arm),patch('tests.run_causal_trials.sandbox_controls',return_value={}),patch('builtins.print'):
                r=run_trials(output)
            self.assertEqual(calls,['gpt-6-luna','gpt-6.1-sol','gpt-6-astra'])
            self.assertEqual(r['passed'],3);self.assertEqual(r['native_turn_requests'],3);self.assertTrue(r['complete_design'])

    def test_quality_failure_is_retained_but_infrastructure_stops(self):
        samples=[{'status':'finished','terminal':'completed','quality_admissible':True,'inference_requests':1,'output_check':False},
                 {'status':'finished','failure':'owned_harness_failure','inference_requests':1,'output_check':False}]
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_causal_trials.run_arm',side_effect=samples),patch('tests.run_causal_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new')
        self.assertEqual(r['quality_attempts'],1);self.assertEqual(r['passed'],0);self.assertTrue(r['campaign_stopped'])
        self.assertEqual(r['native_turn_requests'],2)

    def test_interrupt_and_budget_cannot_expand_quota(self):
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_causal_trials.run_arm',side_effect=KeyboardInterrupt),patch('tests.run_causal_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new')
        self.assertEqual(r['native_turn_requests'],1);self.assertTrue(r['campaign_stopped'])
        for v in (0,4,True):
            with self.assertRaises(ValueError):run_trials(Path('unused'),v)

    def test_unknown_grader_execution_is_excluded_and_stops_calls(self):
        sample={'status':'finished','terminal':'completed','quality_admissible':True,
                'inference_requests':1,'output_check':False,'checks':{'execution':False}}
        with tempfile.TemporaryDirectory() as tmp,patch('tests.run_causal_trials.run_arm',return_value=sample) as call,patch('tests.run_causal_trials.sandbox_controls',return_value={}),patch('builtins.print'):
            r=run_trials(Path(tmp)/'new')
        self.assertEqual(call.call_count,1);self.assertEqual(r['quality_attempts'],0)
        self.assertTrue(r['campaign_stopped']);self.assertEqual(r['native_turn_requests'],1)


if __name__=='__main__':unittest.main()
