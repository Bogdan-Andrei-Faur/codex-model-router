import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.bridge.companion_activity import CompanionActivity, ITEMS
from codex_model_router.bridge.router import Router


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.activity = CompanionActivity()
        self.rows = {'a': {'turn_id': 't', 'status': 'active'}}
        self.activity.begin('a', 't')

    def send(self, method, **params):
        self.activity.observe({'method': method, 'params': {'threadId': 'a', 'turnId': 't', **params}}, self.rows)

    def kind(self):
        return self.activity.project('a')['kind']

    def request(self, rid, blocking=True, approval=False):
        self.activity.observe({'id': rid, 'method': 'item/permissions/requestApproval' if approval else 'item/tool/requestUserInput',
                               'params': {'threadId': 'a', 'turnId': 't', 'itemId': 'i', 'isBlocking': blocking,
                                          'questions': [{'question': 'PRIVATE QUESTION'}]}}, self.rows)

    def test_item_lifecycles_keep_concurrent_work_and_ignore_late_deltas(self):
        self.send('item/started', item={'id': 'r', 'type': 'reasoning', 'text': 'PRIVATE'})
        self.send('item/started', item={'id': 'c', 'type': 'commandExecution', 'command': 'PRIVATE'})
        self.assertEqual(self.kind(), 'executing')
        self.send('item/completed', item={'id': 'c', 'type': 'commandExecution'})
        self.assertEqual(self.kind(), 'thinking')
        self.send('item/completed', item={'id': 'r', 'type': 'reasoning'})
        self.send('item/reasoning/textDelta', itemId='r', delta='PRIVATE')
        self.assertEqual(self.kind(), 'working')
        self.assertNotIn('PRIVATE', json.dumps(self.activity.states, default=list))

    def test_nonblocking_input_keeps_pose_and_requests_resolve_independently(self):
        self.send('item/started', item={'id': 'r', 'type': 'reasoning'})
        self.request('one', False); self.request('two', False)
        self.assertEqual(self.kind(), 'thinking')
        self.assertEqual(self.activity.project('a')['attention'], ['input'])
        self.activity.response({'id': 'one', 'result': {'answers': {'PRIVATE': 'PRIVATE'}}})
        self.assertEqual(self.activity.project('a')['attention'], ['input'])
        self.send('serverRequest/resolved', requestId='two')
        self.assertEqual(self.activity.project('a')['attention'], [])
        self.assertNotIn('PRIVATE', json.dumps(self.activity.project('a')))

    def test_blocking_approval_and_typed_request_ids(self):
        self.request(1, approval=True); self.request('1')
        self.assertEqual(self.kind(), 'approval')
        self.activity.response({'id': 1, 'result': {'decision': 'accept'}})
        self.assertEqual(self.kind(), 'question')
        self.activity.response({'id': '1', 'error': {'message': 'PRIVATE'}})
        self.assertEqual(self.kind(), 'working')

    def test_native_wait_flags_and_unknown_purpose_remain_neutral(self):
        self.send('thread/status/changed', status={'type': 'active', 'activeFlags': ['waitingOnApproval', 'PRIVATE']})
        self.assertEqual(self.kind(), 'approval')
        self.send('thread/status/changed', status={'type': 'active', 'activeFlags': ['waitingOnUserInput']})
        self.assertEqual(self.kind(), 'question')
        self.send('thread/status/changed', status={'type': 'active', 'activeFlags': []})
        self.assertEqual(self.kind(), 'working')

    def test_retry_failure_interruption_and_terminal_cleanup(self):
        self.request('one'); self.send('error', willRetry=True, error={'message': 'PRIVATE'})
        self.assertEqual(self.kind(), 'question')
        self.activity.response({'id': 'one', 'result': {}})
        self.assertEqual(self.kind(), 'retrying')
        self.send('item/started', item={'id': 'r', 'type': 'reasoning'})
        self.assertEqual(self.kind(), 'thinking')
        self.send('error', willRetry=False)
        self.assertEqual(self.kind(), 'error')
        self.send('turn/completed', turn={'id': 't', 'status': 'interrupted'})
        self.assertEqual(self.kind(), 'interrupted')
        self.assertEqual(self.activity.project('a')['attention'], [])
        self.send('item/started', item={'id': 'late', 'type': 'reasoning'})
        self.assertEqual(self.kind(), 'interrupted')

    def test_new_turn_rejects_old_events_and_resolution(self):
        self.request('old'); self.activity.begin('a', 'new'); self.rows['a']['turn_id'] = 'new'
        self.send('item/started', item={'id': 'late', 'type': 'reasoning'})
        self.send('error', willRetry=False)
        self.send('turn/completed', turn={'id': 't', 'status': 'failed'})
        self.assertEqual(self.kind(), 'working')
        self.activity.begin('a', 't')
        self.assertEqual(self.activity.project('a')['turn_id'], 'new')
        self.activity.response({'id': 'old', 'result': {}})
        self.assertEqual(self.kind(), 'working')

    def test_reconnect_recovers_only_explicit_snapshot_activity(self):
        self.request('one'); self.send('item/started', item={'id': 'r', 'type': 'reasoning'})
        self.activity.snapshot('a', {'status': {'type': 'active', 'activeFlags': []}})
        self.assertEqual(self.kind(), 'working'); self.assertEqual(self.activity.project('a')['attention'], [])
        self.assertIsNone(self.activity.project('a')['turn_id'])
        self.activity.snapshot('a', {'status': {'type': 'active', 'activeFlags': ['waitingOnApproval']},
                                  'turns': [{'id': 'new', 'status': 'inProgress', 'items': [
                                      {'id': 'done', 'type': 'commandExecution', 'status': 'completed'},
                                      {'id': 'live', 'type': 'fileChange', 'status': 'inProgress'}]}]})
        self.assertEqual(self.kind(), 'approval')
        self.assertEqual(list(self.activity.states['a']['items'].values()), ['editing'])
        self.assertEqual(CompanionActivity().states, {})

    def test_item_variants_compaction_and_overflow(self):
        for item_type, expected in ITEMS.items():
            self.send('item/started', item={'id': item_type, 'type': item_type})
            self.assertEqual(self.kind(), expected)
            self.send('item/completed', item={'id': item_type, 'type': item_type})
        for i in range(260):
            self.send('item/started', item={'id': str(i), 'type': 'reasoning'})
        self.assertEqual(self.kind(), 'unknown')
        self.assertLessEqual(len(self.activity.states['a']['items']), 256)

    def test_thread_scoped_elicitation_and_review_do_not_guess_question_content(self):
        self.activity.snapshot('a', {'status': {'type': 'active', 'activeFlags': []}})
        self.activity.observe({'id': 'mcp', 'method': 'mcpServer/elicitation/request',
                               'params': {'threadId': 'a', 'turnId': None, 'message': 'PRIVATE', 'url': 'PRIVATE'}}, self.rows)
        self.assertEqual(self.kind(), 'question')
        self.assertEqual(self.activity.project('a')['scope'], 'thread')
        self.activity.response({'id': 'mcp', 'result': {'action': 'cancel'}})
        self.assertEqual(self.kind(), 'working')
        self.activity.begin('a', 'review'); self.rows['a']['turn_id'] = 'review'
        self.send('item/completed', turnId='review', item={'id': 'mode', 'type': 'enteredReviewMode'})
        self.assertEqual(self.kind(), 'reviewing')
        self.send('item/completed', turnId='review', item={'id': 'exit', 'type': 'exitedReviewMode'})
        self.assertEqual(self.kind(), 'working')

    def test_plan_metadata_has_no_sticky_completed_planning_pose(self):
        self.send('turn/plan/updated', plan=[{'step': 'PRIVATE', 'status': 'in_progress'}])
        self.assertEqual(self.kind(), 'planning')
        self.send('turn/plan/updated', plan=[{'step': 'PRIVATE', 'status': 'completed'}])
        self.assertEqual(self.kind(), 'working')

    def test_uncorrelated_error_and_reconnect_do_not_retain_retry(self):
        self.send('error', turnId=None, willRetry=False)
        self.assertEqual(self.kind(), 'working')
        self.send('error', willRetry=True)
        self.assertEqual(self.kind(), 'retrying')
        self.activity.snapshot('a', {'status': {'type': 'active', 'activeFlags': []}})
        self.assertEqual(self.kind(), 'working')


class BridgeActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name); config = root / 'config.json'
        config.write_text(json.dumps({'enabled': False}))
        self.router = Router(config, root / 'state')

    def server(self, message):
        self.assertTrue(self.router.server_line(json.dumps(message).encode()))

    def test_original_request_response_transport_and_safe_status_projection(self):
        self.server({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': 't'}}})
        request = {'id': 'q', 'method': 'item/tool/requestUserInput', 'params': {'threadId': 'a', 'turnId': 't', 'isBlocking': True, 'questions': ['PRIVATE']}}
        self.server(request)
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'question')
        raw = (json.dumps({'id': 'q', 'result': {'answers': 'PRIVATE'}}) + '\n').encode()
        self.assertEqual(self.router.client_line(raw), raw)
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'working')
        self.assertNotIn('PRIVATE', json.dumps(self.router.threads))
        self.assertEqual(self.router.outbound, [])

    def test_snapshot_and_old_turn_replay_cannot_rewind_rows(self):
        self.router.requests[1] = ('thread/resume', {})
        self.server({'id': 1, 'result': {'thread': {'id': 'a', 'status': {'type': 'active', 'activeFlags': ['waitingOnApproval']}}}})
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'approval')
        for turn in ['old', 'new']:
            self.server({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': turn}}})
        self.server({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': 'old'}}})
        self.server({'method': 'turn/completed', 'params': {'threadId': 'a', 'turn': {'id': 'old', 'status': 'failed'}}})
        self.assertEqual(self.router.threads['a']['turn_id'], 'new')
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'working')

    def test_completed_turn_cannot_be_revived_and_started_snapshot_keeps_flags(self):
        self.server({'method': 'thread/started', 'params': {'thread': {'id': 'a', 'status': {'type': 'active', 'activeFlags': ['waitingOnUserInput']}}}})
        self.assertEqual(self.router.threads['a']['status'], 'active')
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'question')
        self.server({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': 't'}}})
        self.server({'method': 'turn/completed', 'params': {'threadId': 'a', 'turn': {'id': 't', 'status': 'completed'}}})
        self.server({'method': 'turn/started', 'params': {'threadId': 'a', 'turn': {'id': 't'}}})
        self.server({'method': 'item/started', 'params': {'threadId': 'a', 'turnId': 't', 'item': {'id': 'late', 'type': 'contextCompaction'}}})
        self.assertEqual(self.router.threads['a']['status'], 'completed')
        self.assertEqual(self.router.threads['a']['activity']['kind'], 'done')


if __name__ == '__main__':
    unittest.main()
