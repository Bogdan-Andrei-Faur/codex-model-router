"""Metadata-only observer. Never owns, answers or changes native RPC messages."""
import time


ITEMS = {
    'reasoning': 'thinking', 'agentMessage': 'writing', 'assistantMessage': 'writing',
    'plan': 'planning', 'commandExecution': 'executing', 'fileChange': 'editing',
    'webSearch': 'searching', 'mcpToolCall': 'tool', 'dynamicToolCall': 'tool',
    'collabAgentToolCall': 'collaborating', 'collabToolCall': 'collaborating',
    'imageView': 'inspecting', 'imageGeneration': 'generating',
    'contextCompaction': 'compacting',
}
DELTAS = {
    'item/reasoning/textDelta': 'thinking',
    'item/reasoning/summaryTextDelta': 'thinking',
    'item/reasoning/summaryPartAdded': 'thinking',
    'item/agentMessage/delta': 'writing', 'item/plan/delta': 'planning',
    'item/commandExecution/outputDelta': 'executing',
    'item/fileChange/outputDelta': 'editing',
}
REQUESTS = {
    'item/commandExecution/requestApproval': 'approval',
    'item/fileChange/requestApproval': 'approval',
    'item/permissions/requestApproval': 'approval',
    'execCommandApproval': 'approval', 'applyPatchApproval': 'approval',
    'item/tool/requestUserInput': 'input',
    'mcpServer/elicitation/request': 'input',
}
FLAGS = {'waitingOnApproval': 'approval', 'waitingOnUserInput': 'input'}
TERMINAL = {'completed': 'done', 'failed': 'error', 'error': 'error',
            'systemError': 'error', 'interrupted': 'interrupted'}


def identifier(value):
    return isinstance(value, str) and 0 < len(value) <= 200


def request_key(value):
    if type(value) is int:
        return ('int', value)
    if identifier(value):
        return ('str', value)
    return None


class CompanionActivity:
    """Each Router instance is a transport epoch; persisted overlays aren't loaded.

    Only lifecycle identifiers and allowlisted enums enter the reducer. Snapshot
    flags are authoritative for blocking waits. Request counts can also represent
    nonblocking attention. Missing flags never establish reasoning or approval.
    """
    def __init__(self):
        self.states = {}

    def state(self, tid):
        if not identifier(tid):
            return None
        if tid not in self.states:
            if len(self.states) >= 1024:
                self.states.pop(next(iter(self.states)))
            self.states[tid] = {'turn': None, 'closed': False, 'items': {},
                                'finished': set(), 'requests': {}, 'flags': set(),
                                'kind': None, 'review': False, 'overflow': False,
                                'retired': set(), 'snapshot_only': False,
                                'observed': time.time()}
        return self.states[tid]

    def begin(self, tid, turn):
        state = self.state(tid)
        if state is None or not identifier(turn):
            return
        if turn in state['retired']:
            return
        if state['turn'] == turn:
            return  # A duplicate begin cannot revive a completed turn.
        retired = state['retired'] | ({state['turn']} if state['turn'] else set())
        if len(retired) > 128:
            retired = {state['turn']}
        self.states[tid] = {'turn': turn, 'closed': False, 'items': {},
                            'finished': set(), 'requests': {}, 'flags': set(),
                            'kind': 'working', 'review': False, 'overflow': False,
                            'retired': retired, 'snapshot_only': False,
                            'observed': time.time()}

    def preparing(self, tid):
        state = self.state(tid)
        if state is not None:
            self.states[tid] = {'turn': None, 'closed': False, 'items': {},
                                'finished': set(), 'requests': {}, 'flags': set(),
                                'kind': 'preparing', 'review': False, 'overflow': False,
                                'retired': state['retired'] | ({state['turn']} if state['turn'] else set()), 'snapshot_only': False,
                                'observed': time.time()}

    def finish(self, tid, kind):
        state = self.state(tid)
        if state is None:
            return
        state.update(closed=True, kind=kind, review=False, overflow=False,
                     observed=time.time())
        state['items'].clear(); state['requests'].clear(); state['flags'].clear()

    def snapshot(self, tid, thread):
        # Reconnection clears old item/request identities; only an explicit
        # in-progress snapshot item can recover a specific pose.
        state = self.state(tid)
        if state is None:
            return
        state['items'].clear(); state['requests'].clear(); state['finished'].clear()
        state.update(review=False, overflow=False, turn=None, closed=False, snapshot_only=True, kind=None)
        for turn in thread.get('turns', []) if isinstance(thread.get('turns'), list) else []:
            if isinstance(turn, dict) and turn.get('status') == 'inProgress' and identifier(turn.get('id')):
                self.begin(tid, turn['id']); state = self.states[tid]
                for item in turn.get('items', []) if isinstance(turn.get('items'), list) else []:
                    if isinstance(item, dict) and item.get('status') == 'inProgress':
                        self.item(state, item.get('id'), ITEMS.get(item.get('type')))
                break
        self.status(tid, thread.get('status'))

    def status(self, tid, status):
        state = self.state(tid)
        if state is None or not isinstance(status, dict):
            return
        kind = status.get('type')
        if kind == 'active':
            if state['closed']:
                state.update(closed=False, turn=None, kind='working', snapshot_only=True)
            state['flags'] = {FLAGS[flag] for flag in status.get('activeFlags', [])
                              if isinstance(flag, str) and flag in FLAGS} if isinstance(status.get('activeFlags'), list) else set()
            if not state['closed']:
                state['kind'] = 'working' if state['kind'] not in ('retrying',) else state['kind']
        elif kind in TERMINAL:
            self.finish(tid, TERMINAL[kind])
        elif kind in ('idle', 'notLoaded', 'closed'):
            self.finish(tid, 'idle' if kind == 'idle' else 'unknown')
        state['observed'] = time.time()

    def item(self, state, item_id, kind):
        if not kind or not identifier(item_id) or item_id in state['finished'] or state['overflow']:
            return
        if len(state['items']) + len(state['finished']) >= 256:
            state['overflow'] = True; state['items'].clear()
            return  # Explicit unknown rather than inventing activity after overflow.
        state['items'].pop('__plan__', None)
        if item_id not in state['items']:
            state['items'][item_id] = kind
        state['kind'] = 'working'

    def observe(self, message, rows):
        method = message.get('method'); params = message.get('params')
        if not isinstance(params, dict):
            return
        tid = params.get('threadId')
        if not identifier(tid):
            return
        if method == 'turn/started':
            turn = params.get('turn') or {}
            self.begin(tid, turn.get('id'))
            return
        state = self.state(tid)
        turn = params.get('turn') if method == 'turn/completed' else None
        turn_id = (turn or {}).get('id') if turn is not None else params.get('turnId')
        current = rows.get(tid, {}).get('turn_id')
        if turn_id and current and turn_id != current:
            return
        if state['turn'] is None and identifier(current) and not state['closed'] and not state['snapshot_only']:
            self.begin(tid, current); state = self.states[tid]
        if turn_id and turn_id != state['turn']:
            return
        if method == 'thread/status/changed':
            self.status(tid, params.get('status')); return
        if method in ('thread/closed', 'thread/archived', 'thread/deleted'):
            self.finish(tid, 'unknown'); return
        if method == 'serverRequest/resolved':
            state['requests'].pop(request_key(params.get('requestId')), None)
            state['observed'] = time.time(); return
        if (not state['closed'] and method in REQUESTS and request_key(message.get('id')) is not None
                and (state['turn'] or (method == 'mcpServer/elicitation/request' and not turn_id))):
            if len(state['requests']) < 64:
                blocking = params.get('isBlocking') is not False
                state['requests'][request_key(message['id'])] = (REQUESTS[method], blocking)
            else:
                state['overflow'] = True
            state['observed'] = time.time()
            return
        if state['closed'] or not state['turn']:
            return
        if method in {'turn/completed', 'error', 'item/started', 'item/completed', 'turn/plan/updated'} | set(DELTAS) and not identifier(turn_id):
            return
        state['observed'] = time.time()
        if method == 'turn/completed':
            self.finish(tid, TERMINAL.get((turn or {}).get('status'), 'unknown'))
        elif method == 'error':
            state['kind'] = 'retrying' if params.get('willRetry') is True else 'error'
        elif method in ('item/started', 'item/completed'):
            item = params.get('item') or {}
            item_id = item.get('id'); item_type = item.get('type')
            if item_type in ('enteredReviewMode', 'exitedReviewMode'):
                state['review'] = item_type == 'enteredReviewMode'
            if method == 'item/started':
                self.item(state, item_id, ITEMS.get(item_type))
            elif identifier(item_id):
                state['items'].pop(item_id, None)
                if len(state['finished']) < 256:
                    state['finished'].add(item_id)
                else:
                    state['overflow'] = True; state['items'].clear()
        elif method in DELTAS:
            self.item(state, params.get('itemId'), DELTAS[method])
        elif method == 'turn/plan/updated':
            plan = params.get('plan')
            if isinstance(plan, list) and any(isinstance(step, dict) and step.get('status') == 'in_progress' for step in plan):
                state['items']['__plan__'] = 'planning'
            else:
                state['items'].pop('__plan__', None)

    def response(self, message):
        if 'method' in message or not ('result' in message or 'error' in message):
            return set()
        key = request_key(message.get('id')); changed = set()
        if key is not None:
            for tid, state in self.states.items():
                if key in state['requests']:
                    state['requests'].pop(key); state['observed'] = time.time()
                    changed.add(tid)
        return changed

    def project(self, tid):
        state = self.states.get(tid)
        if state is None:
            return None
        attention = state['flags'] | {kind for kind, _ in state['requests'].values()}
        blocking = state['flags'] | {kind for kind, block in state['requests'].values() if block}
        kind = state['kind'] or 'unknown'
        if not state['closed'] and kind != 'error':
            if blocking:
                kind = 'approval' if 'approval' in blocking else 'question'
            elif 'compacting' in state['items'].values():
                kind = 'compacting'
            elif kind == 'retrying':
                pass
            elif state['overflow']:
                kind = 'unknown'
            elif state['items']:
                kind = next(reversed(state['items'].values()))
            elif state['review']:
                kind = 'reviewing'
        return {'version': 1, 'turn_id': state['turn'], 'kind': kind,
                'scope': 'turn' if state['turn'] else 'thread',
                'attention': sorted(attention), 'blocking': bool(blocking),
                'source': 'native', 'observed_at': state['observed']}

    def apply(self, tid, rows):
        projection = self.project(tid)
        if projection is not None and tid in rows:
            rows[tid]['activity'] = projection
