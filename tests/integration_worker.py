"""Independent frozen fixture checks, executed only under verified Seatbelt."""
import copy
import itertools
import json
from pathlib import Path
import resource
import runpy
import sys

# -I excludes cwd from sys.path. Load only this frozen trusted helper explicitly;
# candidate imports still use its restricted importer, never the Python path.
_helpers=runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact=_helpers['exact'];load_modules=_helpers['load_modules']

MODELS=('gpt-6-luna','gpt-6.1-sol','gpt-6-astra')
TARGET={'runtime':'fixture-runtime','thread':'fixture-thread','turn':'fixture-turn'}
TOKENS={'inputTokens':100,'cachedInputTokens':20,'outputTokens':10}


def record(response_id='a',model=MODELS[0],**changes):
    return dict(TARGET,response_id=response_id,model=model,tokens=dict(TOKENS),**changes)


def telemetry_checks(modules):
    normalize=modules['records'].normalize;collect=modules['ledger'].collect
    summarize=modules['totals'].summarize
    a=record();b=record('b',MODELS[1]);changed=record(tokens_override=True)
    changed.pop('tokens_override');changed['tokens']['outputTokens']=11
    checks={'normalization':True,'conflict_dedup':True,'coverage_totals':True,'no_mutation':True}
    invalid=[None,[],{},dict(a,response_id=''),dict(a,model='unknown')]
    invalid += [dict(a,**{k:v}) for k in ('runtime','thread','turn') for v in ('foreign','',None,True)]
    invalid += [dict(a,tokens=v) for v in (None,{},dict(TOKENS,inputTokens=True),
        dict(TOKENS,outputTokens=True),dict(TOKENS,cachedInputTokens=True),
        dict(TOKENS,outputTokens=-1),dict(TOKENS,cachedInputTokens=101),dict(TOKENS,outputTokens=1.5))]
    rows=[(dict(a,private_fixture_value='discarded',timestamp=7),TARGET,a)]
    rows += [(r,TARGET,None) for r in invalid]
    rows += [(a,t,None) for t in (None,{},dict(TARGET,turn=''),dict(TARGET,runtime=True))]
    for response,target,expected in rows:
        original=copy.deepcopy((response,target))
        try:checks['normalization'] &= exact(normalize(response,target),expected)
        except BaseException:checks['normalization']=False
        checks['no_mutation'] &= (response,target)==original
    unique={'responses':[a,b],'conflicts':[]}
    conflict={'responses':[b],'conflicts':['a']}
    datasets=[([],{'responses':[],'conflicts':[]}),([a,a,b,dict(a,extra='ignored')],unique),
        ([a,b,*invalid],unique),([dict(a,turn='foreign')],{'responses':[],'conflicts':[]}),
        ([a,dict(a,model=MODELS[2]),b],conflict)]
    # Every ordering must leave a conflicted ID tombstoned, even after a
    # later repeat of its original valid record; no first/last-write win.
    datasets += [(list(p),conflict) for p in itertools.permutations((a,changed,a,b))]
    for records,expected in datasets:
        original=copy.deepcopy((records,TARGET))
        try:checks['conflict_dedup'] &= exact(collect(records,TARGET),expected)
        except BaseException:checks['conflict_dedup']=False
        complete=bool(expected['responses']) and not expected['conflicts']
        tokens={k:sum(r['tokens'][k] for r in expected['responses']) for k in TOKENS} if complete else None
        summary={'response_count':len(expected['responses']),'conflict_count':len(expected['conflicts']),
            'coverage_complete':complete,'tokens':tokens,
            'models':sorted({r['model'] for r in expected['responses']})}
        try:checks['coverage_totals'] &= exact(summarize(records,TARGET),summary)
        except BaseException:checks['coverage_totals']=False
        checks['no_mutation'] &= (records,TARGET)==original
    return {k:bool(v) for k,v in checks.items()}


def cancellation_checks(modules):
    plan=modules['rules'].plan;reduce=modules['executor'].reduce_event;replay=modules['replay'].apply_events
    checks={'cancellation_contract':True,'terminal_order':True,'no_mutation':True}
    statuses=('running','cancelling','cancelled','completed','failed')
    kinds=('request_cancel','phase_request','native_cancelled','native_completed','native_failed','other')
    def expected_action(state,event):
        if (not isinstance(event,dict) or event.get('turn')!=state['turn']
            or state['status'] not in statuses or type(state['cancel_requested']) is not bool
            or type(state['phase_requests']) is not int or state['phase_requests']<0
            or not isinstance(state['turn'],str) or not state['turn']):return 'ignore'
        if state['status'] in ('cancelled','completed','failed'):return 'ignore'
        kind=event.get('kind')
        if kind=='request_cancel':return 'begin_cancel' if state['status']=='running' and not state['cancel_requested'] else 'ignore'
        if kind=='phase_request':return 'allow_phase' if state['status']=='running' and not state['cancel_requested'] else 'ignore'
        return {'native_cancelled':'finish_cancel','native_completed':'finish_completed','native_failed':'finish_failed'}.get(kind,'ignore')
    def expected_state(state,action):
        result=dict(state)
        if action=='begin_cancel':result.update(status='cancelling',cancel_requested=True)
        elif action=='allow_phase':result['phase_requests']+=1
        elif action.startswith('finish_'):
            result['status']={'finish_cancel':'cancelled','finish_completed':'completed','finish_failed':'failed'}[action]
        return result
    events=[{'turn':turn,'kind':kind} for turn in ('fixture-turn','foreign',None) for kind in kinds]
    events += [None,{},[]]
    states=[{'turn':'fixture-turn','status':s,'cancel_requested':cancel,'phase_requests':3,'preserved':{'value':7}}
        for s in statuses for cancel in (False,True)]
    states += [dict(states[0],**change) for change in ({'turn':''},{'status':'other'},
        {'cancel_requested':1},{'phase_requests':True},{'phase_requests':-1})]
    for state,event in itertools.product(states,events):
        original=copy.deepcopy((state,event));action=expected_action(state,event)
        try:
            checks['cancellation_contract'] &= exact(plan(state,event),action)
            result=reduce(state,event)
            checks['cancellation_contract'] &= exact(result,expected_state(state,action)) and result is not state
        except BaseException:checks['cancellation_contract']=False
        checks['no_mutation'] &= (state,event)==original
    initial=states[0]
    sequences=[[],['request_cancel'],['phase_request','request_cancel','phase_request'],
        ['request_cancel','native_completed','native_cancelled'],
        ['request_cancel','native_cancelled','native_completed'],
        ['request_cancel','native_failed','phase_request'],['native_completed','request_cancel'],
        ['request_cancel','request_cancel','native_cancelled']]
    sequences += [list(p) for p in itertools.permutations(('request_cancel','phase_request','native_cancelled'))]
    for names in sequences:
        events=[{'turn':'fixture-turn','kind':k} for k in names]
        if names:events.insert(0,{'turn':'foreign','kind':'native_cancelled'})
        expected=dict(initial)
        for event in events:expected=expected_state(expected,expected_action(expected,event))
        original=copy.deepcopy((initial,events))
        try:
            result=replay(initial,events)
            checks['terminal_order'] &= exact(result,expected) and result is not initial
        except BaseException:checks['terminal_order']=False
        checks['no_mutation'] &= (initial,events)==original
    return {k:bool(v) for k,v in checks.items()}


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(2,2));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    try:
        sources=json.loads(open(sys.argv[2],encoding='utf-8').read());modules=load_modules(sources)
        handlers={'telemetry-conflicts':telemetry_checks,'cancellation-order':cancellation_checks}
        print(json.dumps(handlers[sys.argv[1]](modules)))
    except BaseException:print(json.dumps({'execution':False}))


if __name__=='__main__':main()
