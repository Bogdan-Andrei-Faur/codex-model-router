"""Independent causal-stock oracle; restricted candidate execution under Seatbelt."""
import copy
import itertools
import json
from pathlib import Path
import resource
import runpy
import sys

helpers=runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact=helpers['exact'];load_modules=helpers['load_modules']
IDS=tuple('abcdef');ACCOUNTS=tuple('ABC')


def canonical(row):
    if not isinstance(row,dict) or set(row)!={'id','deps','kind','source','target','amount'}:return None
    if row['id'] not in IDS or row['target'] not in ACCOUNTS:return None
    if type(row['amount']) is not int or not 1<=row['amount']<=9:return None
    if not isinstance(row['deps'],list) or len(row['deps'])>6 or any(d not in IDS for d in row['deps']):return None
    if row['kind']=='credit':
        if row['source'] is not None:return None
    elif row['kind']=='transfer':
        if row['source'] not in ACCOUNTS or row['source']==row['target']:return None
    else:return None
    return {'id':row['id'],'deps':sorted(set(row['deps'])),'kind':row['kind'],
            'source':row['source'],'target':row['target'],'amount':row['amount']}


def collect_reference(records):
    # Group canonical encodings before deciding; independent of first/last wins.
    groups={}
    for row in records:
        value=canonical(row)
        if value is not None:groups.setdefault(value['id'],set()).add(json.dumps(value,sort_keys=True))
    return {'events':{k:json.loads(next(iter(v))) for k,v in groups.items() if len(v)==1},
            'conflicts':sorted(k for k,v in groups.items() if len(v)>1)}


def order_reference(events):
    remaining=set(events);done=[]
    while remaining:
        eligible=[k for k in remaining if set(events[k]['deps'])<=set(done)]
        if not eligible:break
        chosen=min(eligible);done.append(chosen);remaining.remove(chosen)
    return {'order':done,'blocked':sorted(remaining)}


def run_reference(stock,records):
    data=collect_reference(records);remaining=set(data['events']);done=set()
    result={'stock':dict(stock),'applied':[],'rejected':[],'blocked':[],'conflicts':data['conflicts']}
    while remaining:
        choices=[k for k in remaining if set(data['events'][k]['deps'])<=done]
        if not choices:break
        k=min(choices);remaining.remove(k);done.add(k);row=data['events'][k]
        if not set(row['deps'])<=set(result['applied']):result['blocked'].append(k);continue
        source=row['source'];target=row['target'];amount=row['amount']
        if source is not None and result['stock'][source]<amount:result['rejected'].append(k);continue
        result['stock'][target]+=amount
        if source is not None:result['stock'][source]-=amount
        result['applied'].append(k)
    result['blocked']=sorted(set(result['blocked'])|remaining)
    return result


def event(id='a',deps=None,kind='credit',source=None,target='A',amount=2):
    return {'id':id,'deps':deps or [],'kind':kind,'source':source,'target':target,'amount':amount}


def replay_inputs():
    a=event();b=event('b',['a'],'transfer','A','B',2);c=event('c',['b'],'transfer','B','C',2)
    datasets=[[],[a],[a,a],[c,b,a],[event('a',['b']),event('b',['a']),event('c')],
        [event('a',['f']),event('b',['a']),event('c')],
        [event('a',kind='transfer',source='A',target='B',amount=9),event('b',['a']),event('c')],
        [event('c',amount=3),event('a',['c'],'transfer','A','B',1),event('b')],
        [event('a',['a']),event('b')],
        [event('a',kind='transfer',source='A',target='B',amount=3),event('b',['a']),event('c',['b']),event('d')],
        [a,dict(a,amount=3),b,c,event('d')],
        [a,dict(a,amount=True),b,c],
        [event('a',['b','c']),event('a',['c','b','b']),event('b'),event('c')]]
    datasets += [list(p) for p in itertools.permutations((a,dict(a,amount=3),a,b,c))]
    datasets += [list(p) for p in itertools.permutations((a,b,c,event('d',['f'])))]
    for records in datasets:
        for stock in ({'A':0,'B':0,'C':0},{'A':2,'B':0,'C':1},{'A':9,'B':3,'C':0}):
            yield stock,records


def check(modules):
    checks={k:True for k in ('canonical_contract','conflict_tombstones','dependency_order',
                            'atomic_operations','causal_replay','no_mutation')}
    def compare(key,call,args,expected,fresh=False):
        original=copy.deepcopy(args)
        try:
            actual=call(*args);checks[key] &= exact(actual,expected)
            if fresh:checks[key] &= actual['stock'] is not args[0]
        except BaseException:checks[key]=False
        checks['no_mutation'] &= args==original
    valid=event();invalid=[None,{},[],dict(valid,id='x'),dict(valid,target='X'),dict(valid,amount=True),
        dict(valid,amount=0),dict(valid,amount=10),dict(valid,amount=1.5),dict(valid,source='A'),
        dict(valid,kind='other'),dict(valid,deps='a'),dict(valid,deps=['x']),dict(valid,extra=1),
        dict(valid,deps=['a']*7),dict(valid,kind='transfer',source='A',target='A')]
    for row in [valid,event(deps=['c','b','c']),event(deps=['a']),*invalid]:
        compare('canonical_contract',modules['canonical'].normalize,(copy.deepcopy(row),),canonical(row))
    samples=list(replay_inputs())
    for stock,records in samples:
        compare('conflict_tombstones',modules['canonical'].collect,(copy.deepcopy(records),),collect_reference(records))
        compare('causal_replay',modules['replay'].run,(dict(stock),copy.deepcopy(records)),run_reference(stock,records),True)
    # Exhaust all directed graphs on3nodes, including self edges:512 graphs.
    edges=list(itertools.product('abc',repeat=2))
    for mask in range(1<<len(edges)):
        events={k:event(k,[dep for n,(node,dep) in enumerate(edges) if node==k and mask>>n&1]) for k in 'abc'}
        compare('dependency_order',modules['graph'].order,(copy.deepcopy(events),),order_reference(events))
    for events in ({}, {'a':event('a',['f']),'b':event('b')},
                   {'c':event('c'),'a':event('a',['c']),'b':event('b')}):
        compare('dependency_order',modules['graph'].order,(copy.deepcopy(events),),order_reference(events))
    for stock,records in samples[:39]:
        for row in records:
            value=canonical(row)
            if value is None:continue
            expected=run_reference(stock,[dict(value,deps=[])])
            compare('atomic_operations',modules['operations'].apply,(dict(stock),copy.deepcopy(value)),
                {'stock':expected['stock'],'accepted':bool(expected['applied'])},True)
    return {k:bool(v) for k,v in checks.items()}


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(2,2));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    try:
        sources=json.loads(open(sys.argv[2],encoding='utf-8').read())
        print(json.dumps(check(load_modules(sources))))
    except BaseException:print(json.dumps({'execution':False}))


if __name__=='__main__':main()
