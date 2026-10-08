"""At most six synthetic JEV calls; descriptive observations, no calibration gate.

Use only the owner's existing configured connection. Reports retain safe
metadata; no request/provider payloads, credentials or private history.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "src"))
import codex_model_router.routing.candidate_policy as cp
from codex_model_router.routing.decision_engines import _run_jev, build_state, number
from codex_model_router.routing.model_catalog import DEFAULT_ROUTES
from codex_model_router.storage.state_store import atomic_json
from tests.multifile_trials import cases, CASE_HASH
from tests.probe_inference_identity import PROBE_MODELS

LUNA,SOL,ASTRA=PROBE_MODELS


def scenarios():
    multi=cases()
    return [
        {'id':'mechanical','text':'Traduce al inglés: hola','allowed':[(LUNA,'low'),(LUNA,'medium')]},
        {'id':'bounded','text':'Repara una función pequeña y acotada de fechas, con prueba unitaria.','allowed':[(LUNA,'high'),(LUNA,'xhigh'),(SOL,'medium'),(SOL,'high')]},
        *[{'id':c['id'],'text':c['request'],'exercise':c['id'],'allowed':[(SOL,e) for e in ('medium','high','xhigh')]} for c in multi],
        {'id':'infrastructure_retry','text':'Sigue con la refactorización; el intento anterior terminó por timeout de red.',
            'contract':{'remaining_class':'demanding','risk_active':False,'quality_failures':0},'failure':'infrastructure',
            'allowed':[(SOL,'high'),(SOL,'xhigh')]},
        {'id':'remaining_risk','text':'Adelante, continúa con el trabajo pendiente.',
            'contract':{'remaining_class':'critical','risk_active':True,'quality_failures':0},
            'allowed':[(ASTRA,'high'),(ASTRA,'xhigh')]},
    ]


def measurement(scenario, pair, measured):
    """One frozen execution per route; repeated runs are not a retry protocol.

    Never select a convenient first/last result from an unbound sequence. Keep
    all matching attempts visible, including inadmissible and unfinished ones.
    Posterior tags are consistency evidence, not per-response attribution.
    """
    matches=[a for a in measured if isinstance(a,dict) and scenario.get('exercise')
        and pair and a.get('case_id')==scenario['exercise']
        and (a.get('requested_model'),a.get('requested_effort'))==pair]
    result={'measured_exercise_pass':None,'measurement_scope':'not_measured',
        'measurement_reason':'no_matching_execution','matching_execution_attempts':len(matches),
        'admissible_execution_attempts':sum(a.get('quality_admissible') is True for a in matches),
        'unsuccessful_execution_attempts':sum(a.get('output_check') is False for a in matches),
        'observed_failed_checks':sum(isinstance(a.get('checks'),dict)
            and any(v is False for v in a['checks'].values()) for a in matches)}
    if len(matches)>1:
        result['measurement_reason']='ambiguous_execution_sequence';return result
    if not matches:return result
    a=matches[0];checks=a.get('checks');tags=a.get('posterior_model_log_records')
    valid_checks=(isinstance(checks,dict) and bool(checks)
        and all(type(v) is bool for v in checks.values()))
    valid_tags=(isinstance(tags,dict) and bool(tags) and set(tags)=={pair[0]}
        and type(tags[pair[0]]) is int and tags[pair[0]]>0)
    catalog=a.get('native_catalog')
    valid_catalog=(isinstance(catalog,dict) and isinstance(catalog.get(pair[0]),list)
        and pair[1] in catalog[pair[0]])
    valid=(a.get('quality_admissible') is True and a.get('status')=='finished'
        and a.get('terminal')=='completed' and type(a.get('attempt')) is int and a['attempt']==1
        and type(a.get('inference_requests')) is int and a['inference_requests']==1
        and type(a.get('denied_native_requests')) is int and a['denied_native_requests']==0
        and not any(a.get(k) for k in ('failure','cleanup_failure','interrupted'))
        and type(a.get('output_check')) is bool and type(a.get('workflow_complete')) is bool
        and valid_checks and valid_tags and valid_catalog)
    if not valid:
        result['measurement_reason']='incomplete_or_inconsistent_execution';return result
    if a['output_check'] != (all(checks.values()) and a['workflow_complete']):
        result['measurement_reason']='inconsistent_external_checks';return result
    result.update(measured_exercise_pass=a['output_check'],measurement_reason='single_frozen_execution',
        measurement_scope='isolated_exercise_requested_effort_not_posterior_effort_proof')
    return result


def safe_result(value,scenario,choices,measured):
    route=value.get('route');pair=(route.get('model'),route.get('effort')) if isinstance(route,dict) else None
    valid=value.get('status')=='ok' and pair in {(r['model'],r['effort']) for r in choices.values()}
    result={'status':value.get('status') if value.get('status') in ('ok','abstained','invalid','unavailable','not_configured') else 'other',
        'valid_eligible_choice':valid,'reviewed_scope_consistent':pair in scenario['allowed'] if valid else None,
        'selected_route':{'model':pair[0],'effort':pair[1]} if valid else None,
        'confidence':number(value.get('confidence')),
        'eligible_model_count':len({r['model'] for r in choices.values()}),
        'independent_model_judgment_possible':len({r['model'] for r in choices.values()})>1}
    result.update(measurement(scenario,pair if valid else None,measured))
    for k in ('latency_ms','engine_input_tokens','engine_output_tokens','engine_cached_tokens'):
        v=value.get(k)
        if type(v) is int and 0<=v<=1_000_000_000:result[k]=v
    cost=value.get('engine_provider_cost_usd')
    if type(cost) in (float,int) and math.isfinite(cost) and 0<=cost<=10000:result['provider_reported_cost_usd']=cost
    return result


def aggregate(rows):
    costs=[r['provider_reported_cost_usd'] for r in rows
        if type(r.get('provider_reported_cost_usd')) in (int,float)
        and math.isfinite(r['provider_reported_cost_usd']) and 0<=r['provider_reported_cost_usd']<=10000]
    bins={k:{'count':0,'measured_outcomes':0,'measured_passes':0,'scope_label_matches':0} for k in ('below_0_5','0_5_to_0_8','0_8_to_1','unknown')}
    for row in rows:
        confidence=number(row.get('confidence'))
        key='unknown' if confidence is None else 'below_0_5' if confidence<.5 else '0_5_to_0_8' if confidence<.8 else '0_8_to_1'
        b=bins[key];b['count']+=1
        b['scope_label_matches']+=row.get('reviewed_scope_consistent') is True
        b['measured_outcomes']+=type(row.get('measured_exercise_pass')) is bool
        b['measured_passes']+=row.get('measured_exercise_pass') is True
    return {'attempts':len(rows),'statuses':dict(Counter(r.get('status','intent') for r in rows)),
        'confidence_bins':bins,'known_provider_cost_usd':sum(costs) if costs else None,
        'measurement_reasons':dict(Counter(r.get('measurement_reason','legacy_unknown') for r in rows)),
        'provider_cost_coverage_complete':bool(rows) and len(costs)==len(rows),
        'provider_cost_scope':'provider_reported_classifier_calls_not_invoice_or_native_task_cost',
        'calibrated_threshold':None,'statistically_calibrated':False,'policy_activation_eligible':False}


def validate_native(native):
    """Validate the frozen measurement origin before any optional live calls."""
    from tests.multifile_trials import GRADER_HASH
    if (not isinstance(native,dict) or native.get('schema')!='isolated-multifile-trials/1'
        or native.get('case_sha256')!=CASE_HASH
        or native.get('grader_sha256')!=GRADER_HASH):
        raise ValueError('measurement_rubric_mismatch')
    if not isinstance(native.get('attempts'),list) or not all(isinstance(a,dict) for a in native['attempts']):
        raise ValueError('ambiguous_measurement_cohort')


def link_measured(report,native):
    """Offline annotation of existing calls, never new provider requests."""
    validate_native(native)
    if report.get('schema')!='jev-descriptive-trials/1' or report.get('case_sha256')!=CASE_HASH:
        raise ValueError('measurement_rubric_mismatch')
    result=json.loads(json.dumps(report));by_id={s['id']:s for s in scenarios()}
    rows=result.get('attempts');executions=native.get('attempts')
    if (not isinstance(rows,list) or not isinstance(executions,list)
        or not all(isinstance(r,dict) and r.get('case_id') in by_id for r in rows)
        or len({r['case_id'] for r in rows})!=len(rows)):
        raise ValueError('ambiguous_measurement_cohort')
    for row in result['attempts']:
        scenario=by_id[row['case_id']];route=row.get('selected_route')
        pair=(route.get('model'),route.get('effort')) if isinstance(route,dict) else None
        valid=(row.get('status')=='ok' and row.get('valid_eligible_choice') is True
            and pair and pair[0] in PROBE_MODELS and pair[1] in ('low','medium','high','xhigh'))
        row.update(measurement(scenario,pair if valid else None,executions))
    result['summary']=aggregate(result['attempts']);result['measurement_link_provider_calls']=0
    result['measurement_runner_sha256']=native.get('runner_sha256')
    result['measurement_linker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def evaluate(config,state_dir,catalog,output,measured=()):
    rows=scenarios();output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'schema':'jev-descriptive-trials/1','max_provider_calls':6,'case_sha256':CASE_HASH,
        'rubric_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'label_scope':'reviewed_route_eligibility_is_not_demonstrated_answer_quality',
        'runtime_health_or_configuration_changed':False,'attempts':[],'policy_activation_eligible':False}
    for scenario in rows:
        assessment=cp.profile(scenario['text'],contract=scenario.get('contract'),failure=scenario.get('failure','none'))
        choices=cp.candidates(DEFAULT_ROUTES,catalog,assessment)
        state=build_state(scenario['text'],{'present':False,'count':0},None,None,scenario.get('failure')=='infrastructure')
        state.update(candidate_policy_version=9,work_context=assessment)
        intent={'case_id':scenario['id'],'status':'intent','work_class':assessment['work_class']}
        report['attempts'].append(intent);atomic_json(output/'report.json',report)
        try:value=_run_jev(config,state_dir,state,choices)
        except Exception:value={'status':'unavailable'}
        intent.update(safe_result(value,scenario,choices,measured));atomic_json(output/'report.json',report)
        print(json.dumps({'case':scenario['id'],'status':intent['status'],'route':intent['selected_route'],
            'confidence':intent['confidence'],'measured_pass':intent['measured_exercise_pass']}),flush=True)
    report['summary']=aggregate(report['attempts']);atomic_json(output/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true')
    p.add_argument('--output',type=Path);p.add_argument('--multifile-report',type=Path);a=p.parse_args()
    if not a.live:
        print(json.dumps({'cases':[s['id'] for s in scenarios()],'provider_calls':0,'calibrated_threshold':None}));return 0
    if not a.output or a.output.exists() or not a.multifile_report:p.error('requires new output and native catalog evidence')
    native=json.loads(a.multifile_report.read_text());validate_native(native)
    measured=native['attempts']
    catalog=next((x['native_catalog'] for x in measured if x.get('native_catalog')),None)
    if not catalog:raise ValueError('native_catalog_missing')
    config=json.loads((ROOT/'config.local.json').read_text(encoding='utf-8-sig'))
    report=evaluate(config,ROOT/'state',catalog,a.output,measured)
    print(json.dumps(report['summary']));return 0


if __name__=='__main__':sys.exit(main())
