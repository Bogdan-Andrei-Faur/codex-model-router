"""Native plan notifications drive safe live snapshots without routing mutations."""
import json
import tempfile
import unittest
from pathlib import Path

from phase_tracking import native_plan
from router import Router


class LivePipelineTests(unittest.TestCase):
    def test_native_schema_states_and_content_free_projection(self):
        projected = native_plan({'turnId':'turn', 'explanation':'PRIVATE_EXPLANATION', 'plan':[
            {'step':'Investigate PRIVATE_PATH', 'status':'completed'},
            {'step':'Implement PRIVATE_SOURCE', 'status':'inProgress'},
            {'step':'Validate PRIVATE_SECRET', 'status':'pending'}]})
        self.assertEqual([s['state'] for s in projected['steps']], ['completed','active','pending'])
        self.assertEqual([s['label'] for s in projected['steps']], ['Investigar','Implementar','Validar'])
        self.assertNotIn('PRIVATE',json.dumps(projected))
        for plan in [None, [{}], [{'step':'x','status':'invented'}], [{'step':3,'status':'pending'}]]:
            self.assertIsNone(native_plan({'turnId':'turn','plan':plan}))
        self.assertEqual(native_plan({'turnId':'turn','plan':[]})['steps'],[])

    def test_live_updates_reject_wrong_turn_and_do_not_finish_unreported_steps(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);router=Router(root/'config.json',root)
            def send(method, **params):
                message=json.dumps({'method':method,'params':{'threadId':'task',**params}})
                self.assertTrue(router.server_line(message))
            send('turn/started',turn={'id':'one'})
            plan=[{'step':'Investigate PRIVATE', 'status':'completed'}, {'step':'Implement PRIVATE','status':'inProgress'}]
            send('turn/plan/updated',turnId='old',plan=plan)
            self.assertNotIn('live_plan',router.threads['task'])
            send('turn/plan/updated',turnId='one',plan=plan)
            row=router.threads['task'];self.assertEqual(row['live_plan']['steps'][1]['state'],'active')
            snapshot=json.loads(next(root.glob('status-*.json')).read_text())
            self.assertEqual(snapshot['agent_threads']['task']['live_plan'],row['live_plan'])
            self.assertNotIn('PRIVATE',json.dumps(snapshot))
            send('turn/completed',turn={'id':'one','status':'completed'})
            self.assertEqual(row['live_plan']['steps'][1]['state'],'active','Turn end must not forge step completion')
            send('turn/plan/updated',turnId='one',plan=[])
            self.assertEqual(len(row['live_plan']['steps']),2,'Late event must not alter ended turn')
            send('turn/started',turn={'id':'two'})
            self.assertNotIn('live_plan',row,'New turn must reset old plan')
            send('turn/plan/updated',turnId='one',plan=plan)
            self.assertNotIn('live_plan',row)
            send('turn/plan/updated',turnId='two',plan=plan)
            send('turn/plan/updated',turnId='two',plan=[])
            self.assertEqual(row['live_plan']['steps'],[])

if __name__=='__main__':unittest.main()
