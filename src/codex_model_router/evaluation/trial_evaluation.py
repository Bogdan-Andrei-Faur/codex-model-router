"""Explicit paired trials. Failed attempts count; incomplete cost stays unknown."""
from collections import defaultdict, Counter
import math
import time
from pathlib import Path
from codex_model_router.routing.model_catalog import estimate_standard_usage
from codex_model_router.evaluation.outcome_evaluation import LABEL
from codex_model_router.storage.state_store import append_record, read_records, file_lock

TOKENS = ('inputTokens', 'cachedInputTokens', 'outputTokens')


def record_attempt(state, decision_id, evaluation_id, workload_id, run_id, arm, attempt, origin, checks, split):
    if (not isinstance(checks,list) or not checks or len(checks)>100 or
            not all(isinstance(x,str) and LABEL.fullmatch(x) for x in (evaluation_id,workload_id,run_id,*checks)) or
            len(set(checks)) != len(checks) or arm not in ('baseline','candidate') or
            origin not in ('real','synthetic') or split not in ('adjustment','held_out') or
            type(attempt) is not int or not 1<=attempt<=100):
        raise ValueError('invalid_trial_metadata')
    state=Path(state)
    with file_lock(state/'outcomes.lock'):
        rows=list(read_records(state/'history.jsonl'))
        own=[r for r in rows if r.get('decision_id')==decision_id]
        if not any(r.get('event')=='decision_created' for r in own) or not any(r.get('event')=='decision_completed' and r.get('status') in ('completed','failed','interrupted') for r in own):
            raise ValueError('decision_not_terminal')
        if any(r.get('event')=='trial_attempt' for r in own):
            raise ValueError('attempt_already_bound')
        cohort=(evaluation_id,workload_id,run_id,arm,origin)
        for r in rows:
            if r.get('event')=='trial_attempt' and tuple(r.get(k) for k in ('evaluation_id','workload_id','trial_run_id','evaluation_arm','workload_origin'))==cohort:
                if r.get('attempt_index')==attempt or r.get('trial_required_checks')!=checks or r.get('trial_split')!=split:
                    raise ValueError('trial_membership_conflict')
        append_record(state,{'schema':3,'event':'trial_attempt','time':time.time(),'decision_id':decision_id,
            'evaluation_id':evaluation_id,'workload_id':workload_id,'trial_run_id':run_id,
            'evaluation_arm':arm,'workload_origin':origin,'attempt_index':attempt,
            'trial_required_checks':checks,'trial_split':split})


def finite(v):
    return type(v) in (int,float) and math.isfinite(v) and v>=0


def attempt_metrics(rows):
    created=next((r for r in rows if r.get('event')=='decision_created'),{})
    baseline=next((r for r in rows if r.get('event')=='decision_usage_baseline'),{})
    terminal=next((r for r in reversed(rows) if r.get('event')=='decision_completed'),{})
    total=next((r for r in reversed(rows) if r.get('event')=='decision_usage_total'),{})
    delta={}
    if all(finite(baseline.get('usage_baseline_'+k)) and finite(total.get('native_total_'+k)) and total['native_total_'+k]>=baseline['usage_baseline_'+k] for k in TOKENS):
        delta={k:total['native_total_'+k]-baseline['usage_baseline_'+k] for k in TOKENS}
    observed={}
    for r in rows:
        if r.get('event')=='inference_observed' and r.get('evidence_confidence')=='confirmed' and isinstance(r.get('inference_event_id'),str) and r['inference_event_id']:
            observed[(r.get('runtime_instance'),r.get('thread'),r.get('turn_id'),r['inference_event_id'])]=r
    estimates=[estimate_standard_usage(r.get('observed_model'),r) for r in observed.values()]
    names=dict(zip(TOKENS,('inference_input_tokens','inference_cached_tokens','inference_output_tokens')))
    complete=bool(delta and observed and all(estimates) and
        all(all(finite(r.get(names[k])) for k in TOKENS) for r in observed.values()) and
        all(sum(r.get(names[k],0) for r in observed.values())==delta[k] for k in TOKENS))
    classifier={}; legacy=0
    for i,r in enumerate(rows):
        if r.get('event') not in ('engine_comparison','policy_comparison_jev') or r.get('routing_engine')!='jev':
            continue
        key=r.get('engine_comparison_id')
        if not key:
            legacy+=1; key=('legacy',i)
        classifier[key]=r
    classifier_complete=not legacy and all(finite(r.get('engine_provider_cost_usd')) for r in classifier.values())
    checks={r['check_id']:r.get('check_result') for r in rows if r.get('event')=='outcome_check' and r.get('check_source')=='external_reported' and isinstance(r.get('check_id'),str)}
    duration=terminal['time']-created['time'] if finite(created.get('time')) and finite(terminal.get('time')) and terminal['time']>=created['time'] else None
    return {'terminal':terminal.get('status'),'checks':checks,'native_token_delta':delta,
        'confirmed_responses':len(observed),'consumption_coverage_complete':complete and classifier_complete,
        'estimated_standard_credits':sum(e.get('estimated_codex_standard_credits',0) for e in estimates) if complete else None,
        'classifier_provider_reported_usd':sum(r['engine_provider_cost_usd'] for r in classifier.values()) if classifier_complete else None,
        'classifier_calls':len(classifier),'retry_notifications':sum(r.get('event')=='native_turn_error' and r.get('will_retry') is True for r in rows),
        'duration_seconds':duration}


def evaluate_trials(records):
    decisions=defaultdict(list)
    for r in records:
        if isinstance(r.get('decision_id'),str): decisions[r['decision_id']].append(r)
    cohorts=defaultdict(lambda:defaultdict(list)); excluded=Counter()
    for rows in decisions.values():
        members=[r for r in rows if r.get('event')=='trial_attempt']
        if len(members)!=1:
            if members: excluded['ambiguous_membership']+=1
            continue
        m=members[0]; arm=m.get('evaluation_arm')
        key=tuple(m.get(k) for k in ('evaluation_id','workload_id','trial_run_id','workload_origin','trial_split'))
        if arm not in ('baseline','candidate') or not all(isinstance(k,str) and k for k in key):
            excluded['invalid_membership']+=1; continue
        cohorts[key][arm].append((m,attempt_metrics(rows)))
    results=[]
    for key,arms in cohorts.items():
        if set(arms)!={'baseline','candidate'}:
            excluded['unpaired_trial']+=1; continue
        required_sets={tuple(m.get('trial_required_checks',[])) for runs in arms.values() for m,_ in runs}
        if len(required_sets)!=1 or not next(iter(required_sets)):
            excluded['different_check_sets']+=1; continue
        required=set(next(iter(required_sets))); combined={}; invalid=False
        for arm,runs in arms.items():
            runs.sort(key=lambda r:r[0].get('attempt_index',0))
            if [m.get('attempt_index') for m,_ in runs]!=list(range(1,len(runs)+1)):
                invalid=True; break
            final=runs[-1][1]; complete=all(r['consumption_coverage_complete'] for _,r in runs)
            combined[arm]={'attempts':len(runs),'passed':final['terminal']=='completed' and set(final['checks'])==required and all(v=='passed' for v in final['checks'].values()),
                'consumption_coverage_complete':complete,
                'estimated_standard_credits':sum(r['estimated_standard_credits'] for _,r in runs) if complete else None,
                'classifier_provider_reported_usd':sum(r['classifier_provider_reported_usd'] for _,r in runs) if complete else None,
                'retry_notifications':sum(r['retry_notifications'] for _,r in runs),
                'duration_seconds':sum(r['duration_seconds'] for _,r in runs) if all(r['duration_seconds'] is not None for _,r in runs) else None}
        if invalid:
            excluded['missing_or_repeated_attempt']+=1; continue
        results.append({'workload_origin':key[3],'trial_split':key[4],'baseline':combined['baseline'],'candidate':combined['candidate']})
    return {'quality_source':'externally_reported_executed_checks_not_independently_attested',
            'matched_trials':len(results),'results':results,'excluded':dict(excluded),
            'estimate_basis':'standard_equivalent_not_billed','billed_cost_observed':False,
            'cost_currencies':'Codex credits and provider USD are separate, never summed.',
            'causal_savings_demonstrated':False}
