"""Trusted bounded worker. Run only through coding_trials.grade_source sandbox."""
import copy
import json
import math
import resource
import sys


def confidence_checks(fn):
    groups={
        'edge_cases':[(None,None),([],None),({},None),({'confidence':0},0),({'confidence':1},1),
            ({'confidence':True},None),({'confidence':'0.9'},None),({'confidence':float('nan')},None),
            ({'confidence':float('inf')},None),({'confidence':-0.1},None),({'confidence':1.1},None),
            ({'confidence':0.45678},0.45678)],
        'nested_conflict':[({'answers':{'route':{'confidence':0.71}}},0.71),
            ({'providerMetadata':{'typesafe':{'confidence':{'route':0.83}}}},0.83),
            ({'confidence':0.9,'answers':{'route':{'confidence':0.61}},'providerMetadata':{'typesafe':{'confidence':{'route':0.73}}}},0.61),
            ({'confidence':False,'answers':{'route':{'confidence':0.62}}},0.62),
            ({'answers':[],'providerMetadata':{'typesafe':[]}},None),
            ({'answers':{'route':None},'providerMetadata':None},None)],
        'probability_not_confidence':[({'choices':[{'probability':0.99}]},None),
            ({'choices':[{'probability':0.99}],'confidence':0.37},0.37)]}
    checks={};unchanged=True;count=0
    for group,rows in groups.items():
        passed=True
        for value,expected in rows:
            # NaN cannot be compared for equality; JSON serialization is stable.
            before=json.dumps(value,sort_keys=True);count+=1
            try:
                result=fn(value)
                passed &= (result is None if expected is None else type(result) in (int,float) and result==expected)
            except BaseException:passed=False
            unchanged &= before==json.dumps(value,sort_keys=True)
        checks[group]=bool(passed)
    checks['no_mutation']=unchanged
    return checks,count


def transition_checks(fn):
    models=('gpt-6-luna','gpt-6.1-sol','gpt-6-astra')
    catalog={m:['medium','high'] for m in models}
    checks={k:True for k in ('supported_routes','astra_boundary','review_boundary','no_mutation')};count=0
    for current in models:
        for target in models:
            for effort in ('medium','high','ultra'):
                for active in (False,True):
                    count+=1;before=copy.deepcopy(catalog)
                    if effort=='ultra':group='supported_routes';expected={'action':'reject','reason':'unsupported_route'}
                    elif active and current!=target:
                        group='astra_boundary' if 'gpt-6-astra' in (current,target) else 'review_boundary'
                        expected={'action':'defer','reason':group}
                    else:group='supported_routes';expected={'action':'apply','reason':'allowed'}
                    try:checks[group] &= fn(current,target,effort,active,catalog)==expected
                    except BaseException:checks[group]=False
                    checks['no_mutation'] &= catalog==before
    invalid=[('unknown',models[0],'high',catalog),(models[0],'unknown','high',catalog),
             (models[0],models[1],'high',{}),(models[0],models[1],'high',None),
             (models[0],models[1],'high',[]),(models[0],models[1],'high',{models[1]:None})]
    for current,target,effort,allowed in invalid:
        count+=1;before=copy.deepcopy(allowed)
        try:checks['supported_routes'] &= fn(current,target,effort,True,allowed)=={'action':'reject','reason':'unsupported_route'}
        except BaseException:checks['supported_routes']=False
        checks['no_mutation'] &= before==allowed
    return {k:bool(v) for k,v in checks.items()},count


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(2,2))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    source=open(sys.argv[2],encoding='utf-8').read()
    allowed={}
    import builtins
    for name in ('dict','list','tuple','set','str','int','float','bool','type','isinstance','len','sorted',
                 'min','max','sum','enumerate','range','zip','any','all','abs','round','Exception','ValueError','TypeError','OverflowError'):
        allowed[name]=getattr(builtins,name)
    def math_only(name,globals=None,locals=None,fromlist=(),level=0):
        if name!='math' or level:raise ImportError('import_rejected')
        return math
    allowed['__import__']=math_only
    namespace={'__builtins__':allowed,'math':math}
    try:
        exec(compile(source,'<candidate>','exec'),namespace)
        if sys.argv[1]=='confidence-repair':checks,count=confidence_checks(namespace['confidence'])
        else:checks,count=transition_checks(namespace['transition'])
        print(json.dumps({'checks':checks,'cases':count}))
    except BaseException:
        # Never emit model-produced text, exceptions or traceback.
        print(json.dumps({'checks':{'execution':False},'cases':0}))


if __name__=='__main__':main()
