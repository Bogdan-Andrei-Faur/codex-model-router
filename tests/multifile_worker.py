"""Trusted external integration checks; run under restrictive Seatbelt only."""
import builtins
import copy
import json
import math
import resource
import sys
import types


def exact(actual,expected):
    try:return type(actual) is type(expected) and json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
    except (TypeError,ValueError):return False


def load_modules(sources):
    modules={};loading=set()
    allowed={name:getattr(builtins,name) for name in ('dict','list','tuple','set','str','int','float','bool',
        'type','isinstance','len','sorted','min','max','sum','enumerate','range','zip','any','all','abs','round',
        'Exception','ValueError','TypeError','OverflowError')}
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        if level:raise ImportError('relative_import_rejected')
        if name=='math':return math
        if name not in sources or name in loading:raise ImportError('import_rejected')
        if name not in modules:
            loading.add(name);m=types.ModuleType(name);m.__dict__['__builtins__']=allowed
            exec(compile(sources[name],'<candidate-module>','exec'),m.__dict__)
            modules[name]=m;loading.remove(name)
        return modules[name]
    allowed['__import__']=importer
    for name in sources:importer(name)
    return modules


def usage_checks(modules):
    delta=modules['snapshots'].delta;aggregate=modules['session'].aggregate
    zero={'inputTokens':0,'outputTokens':0,'cachedInputTokens':0}
    first={'inputTokens':100,'outputTokens':20,'cachedInputTokens':40}
    second={'inputTokens':130,'outputTokens':25,'cachedInputTokens':50}
    rows=[(zero,first,first),(first,second,{'inputTokens':30,'outputTokens':5,'cachedInputTokens':10}),
          (first,first,zero),(first,zero,None),(zero,{'inputTokens':1,'outputTokens':2},None),
          (None,first,None),(zero,dict(first,inputTokens=True),None),(zero,dict(first,cachedInputTokens=101),None)]
    checks={'snapshot_contract':True,'no_mutation':True}
    for before,after,expected in rows:
        original=copy.deepcopy((before,after))
        try:checks['snapshot_contract'] &= exact(delta(before,after),expected)
        except BaseException:checks['snapshot_contract']=False
        checks['no_mutation'] &= (before,after)==original
    cases=[([],{'attempts':0,'coverage_complete':False,'tokens':None}),
        ([{'status':'completed','before':zero,'after':first},{'status':'failed','before':first,'after':second}],
         {'attempts':2,'coverage_complete':True,'tokens':second}),
        ([{'status':'failed','before':zero,'after':first}],{'attempts':1,'coverage_complete':True,'tokens':first}),
        ([{'status':'completed','before':zero,'after':first},{'status':'failed','before':first,'after':zero}],
         {'attempts':2,'coverage_complete':False,'tokens':None}),
        ([{'status':'completed','before':zero,'after':None}],{'attempts':1,'coverage_complete':False,'tokens':None})]
    checks['all_attempts_and_coverage']=True
    for attempts,expected in cases:
        original=copy.deepcopy(attempts)
        try:checks['all_attempts_and_coverage'] &= exact(aggregate(attempts),expected)
        except BaseException:checks['all_attempts_and_coverage']=False
        checks['no_mutation'] &= attempts==original
    return {k:bool(v) for k,v in checks.items()}


def transition_checks(modules):
    models=('gpt-6-luna','gpt-6.1-sol','gpt-6-astra');catalog={m:['medium','high'] for m in models}
    checks={'plan_contract':True,'caller_respects_decision':True,'no_mutation':True}
    rows=[(a,b,e,t,catalog) for a in models for b in models for e in ('medium','high','ultra') for t in (False,True)]
    rows += [(models[0],models[1],'high',True,None),(models[0],'unknown','high',True,catalog),
             ('unknown',models[0],'high',False,catalog),(models[0],models[1],'high',True,{models[1]:None})]
    for current,target,effort,active,allowed in rows:
        if current not in models or target not in models or not isinstance(allowed,dict) or not isinstance(allowed.get(target),list) or effort not in allowed[target]:
            decision={'action':'reject','reason':'unsupported_route'}
        elif active and current!=target:
            decision={'action':'defer','reason':'astra_boundary' if 'gpt-6-astra' in (current,target) else 'review_boundary'}
        else:decision={'action':'apply','reason':'allowed'}
        state={'model':current,'effort':'medium','active_turn':active,'preserved':'fixture-value'}
        original=copy.deepcopy((state,allowed));expected=dict(state)
        if decision['action']=='apply':expected.update(model=target,effort=effort)
        try:
            checks['plan_contract'] &= exact(modules['policy'].plan(current,target,effort,active,allowed),decision)
            result=modules['executor'].apply_request(state,target,effort,allowed)
            checks['caller_respects_decision'] &= exact(result,{'state':expected,'decision':decision}) and result['state'] is not state
        except BaseException:
            checks['plan_contract']=False;checks['caller_respects_decision']=False
        checks['no_mutation'] &= (state,allowed)==original
    return {k:bool(v) for k,v in checks.items()}


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(2,2));resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    try:
        sources=json.loads(open(sys.argv[2],encoding='utf-8').read())
        modules=load_modules(sources)
        checks=usage_checks(modules) if sys.argv[1]=='usage-integration' else transition_checks(modules)
        print(json.dumps(checks))
    except BaseException:print(json.dumps({'execution':False}))


if __name__=='__main__':main()
