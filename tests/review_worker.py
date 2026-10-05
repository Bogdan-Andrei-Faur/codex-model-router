"""Frozen independent counterexample scorer; no model code is executed."""
import copy
import json
from pathlib import Path
import resource
import runpy
import sys

_helpers=runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact=_helpers['exact'];load_modules=_helpers['load_modules']
DEFECTS={'interval-review':{'B','C','F'},'ordered-review':{'B','D'}}


def integer(value,low,high):return type(value) is int and low<=value<=high


def values(value):return isinstance(value,list) and len(value)<=20 and all(integer(v,-20,20) for v in value)


def interval(value):return isinstance(value,list) and len(value)==2 and all(integer(v,0,20) for v in value) and value[0]<value[1]


def intervals(value):return isinstance(value,list) and len(value)<=6 and all(interval(v) for v in value)


def valid_args(case,function,args):
    keys={'interval-review':{'A':('intervals',),'B':('interval','point'),'C':('window','blocked'),
        'D':('intervals',),'E':('values','size'),'F':('count','size')},
        'ordered-review':{'A':('values',),'B':('values','count'),'C':('shards',),
        'D':('base','attempts','cap'),'E':('values','offset','limit'),'F':('expiry','now')}}
    if not isinstance(args,dict) or set(args)!=set(keys[case][function]):return False
    for key,value in args.items():
        if key in ('interval','window') and not interval(value):return False
        if key in ('intervals','blocked') and not intervals(value):return False
        if key=='values' and not values(value):return False
        bounds={'size':(1,10),'point':(0,20),'count':(0,100 if case=='interval-review' else 20),
            'base':(1,10),'attempts':(0,8),'cap':(1,100),'offset':(0,20),'limit':(0,20),
            'expiry':(0,100),'now':(0,100)}
        if key in bounds and not integer(value,*bounds[key]):return False
        if key=='shards' and not (isinstance(value,list) and len(value)<=10
            and all(isinstance(s,dict) and set(s)<={'a','b','c'} and all(integer(v,0,100) for v in s.values()) for s in value)):return False
    return True


def occupied(intervals):return {i for start,end in intervals for i in range(start,end)}


def portions(points):
    result=[]
    for point in sorted(points):
        if result and result[-1][1]==point:result[-1][1]=point+1
        else:result.append([point,point+1])
    return result


def reference(case,function,args):
    if case=='interval-review':
        if function=='A':return portions(occupied(args['intervals']))
        if function=='B':return args['point'] in range(*args['interval'])
        if function=='C':return portions(set(range(*args['window']))-occupied(args['blocked']))
        if function=='D':return len(occupied(args['intervals']))
        if function=='E':return [args['values'][i:i+args['size']] for i in range(0,len(args['values']),args['size'])]
        if function=='F':return (args['count']+args['size']-1)//args['size']
    if function=='A':return [v for i,v in enumerate(args['values']) if v not in args['values'][:i]]
    if function=='B':
        count=min(args['count'],len(args['values']))
        return [args['values'][len(args['values'])-count+i] for i in range(count)]
    if function=='C':return {k:sum(s.get(k,0) for s in args['shards']) for k in {k for s in args['shards'] for k in s}}
    if function=='D':return [min(args['cap'],args['base']*2**i) for i in range(args['attempts'])]
    if function=='E':return [v for i,v in enumerate(args['values']) if args['offset']<=i<args['offset']+args['limit']]
    if function=='F':return args['now']>=args['expiry']


def score(case,modules,findings):
    shapes=isinstance(findings,list) and len(findings)<=6 and all(isinstance(f,dict)
        and set(f)=={'function','args'} and isinstance(f['function'],str)
        and f['function'] in 'ABCDEF' and len(f['function'])==1 and isinstance(f['args'],dict) for f in findings)
    verified=set();seen=set();false_positives=invalid=duplicates=unexpected=0
    if shapes:
        for finding in findings:
            function=finding['function'];args=finding['args']
            if function in seen:duplicates+=1;continue
            seen.add(function)
            if not valid_args(case,function,args):
                invalid+=1
                if function not in DEFECTS[case]:false_positives+=1
                continue
            module=('windows' if function in 'ABC' else 'batching') if case=='interval-review' else ('ordered' if function in 'ABC' else 'schedule')
            original=copy.deepcopy(args)
            try:
                actual=getattr(modules[module],function)(**args)
                counterexample=not exact(actual,reference(case,function,original)) or not exact(args,original)
            except BaseException:counterexample=True
            if function not in DEFECTS[case]:
                if counterexample:unexpected+=1
                else:false_positives+=1;invalid+=1
            elif counterexample:verified.add(function)
            else:invalid+=1
    checks={'submission_contract':bool(shapes),'all_defects_found':verified==DEFECTS[case],
        'no_false_positives':false_positives==0,'valid_counterexamples':invalid==0 and duplicates==0,
        'oracle_consistent':unexpected==0}
    return {'checks':checks,'reported_findings':len(findings) if isinstance(findings,list) else 0,
        'known_defects':len(DEFECTS[case]),'verified_defects':len(verified),
        'missed_defects':len(DEFECTS[case]-verified),'false_positives':false_positives,
        'invalid_witnesses':invalid,'duplicate_findings':duplicates,'unexpected_counterexamples':unexpected}


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(2,2));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    try:
        case=sys.argv[1];data=json.loads(open(sys.argv[2],encoding='utf-8').read())
        modules=load_modules(data['sources'])
        print(json.dumps(score(case,modules,data['findings'])))
    except BaseException:print(json.dumps({'checks':{'execution':False}}))


if __name__=='__main__':main()
