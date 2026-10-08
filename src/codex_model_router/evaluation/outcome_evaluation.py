"""Explicit external check evidence, never inferred from a completed turn."""
from collections import Counter, defaultdict
import re
import time
import math
from codex_model_router.storage.state_store import append_record, read_records, file_lock
from pathlib import Path

LABEL = re.compile(r'[a-z0-9][a-z0-9_.-]{0,63}\Z')


def record_check(state, decision_id, evaluation_id, workload_id, check_id, arm, result, origin):
    state = Path(state)
    with file_lock(state / 'outcomes.lock'):
        return _record_check(state, decision_id, evaluation_id, workload_id, check_id, arm, result, origin)


def _record_check(state, decision_id, evaluation_id, workload_id, check_id, arm, result, origin):
    """Record a supplied external check result after a native terminal event.

    Evaluation/workload/check labels must be non-personal fixture identifiers.
    This function does not run a check or attest to the truth of the supplied result.
    """
    if not all(isinstance(v, str) and LABEL.fullmatch(v) for v in (evaluation_id, workload_id, check_id)):
        raise ValueError('invalid_fixture_label')
    if arm not in ('baseline', 'candidate') or result not in ('passed', 'failed') or origin not in ('real', 'synthetic'):
        raise ValueError('invalid_check_result')
    rows = [r for r in read_records(state / 'history.jsonl') if r.get('decision_id') == decision_id]
    if not any(r.get('event') == 'decision_created' for r in rows):
        raise ValueError('unknown_decision')
    if not any(r.get('event') == 'decision_completed' and r.get('status') in ('completed','failed','interrupted') for r in rows):
        raise ValueError('decision_not_terminal')
    previous = [r for r in rows if r.get('event') == 'outcome_check']
    identity = (evaluation_id, workload_id, arm, origin)
    if any(tuple(r.get(k) for k in ('evaluation_id','workload_id','evaluation_arm','workload_origin')) != identity for r in previous):
        raise ValueError('decision_check_cohort_conflict')
    stamp = time.time()
    append_record(state, {'schema': 3, 'event': 'outcome_check', 'decision_id':decision_id,
                         'time':stamp, 'time_iso':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(stamp)),
                         'evaluation_id':evaluation_id, 'workload_id':workload_id, 'check_id':check_id,
                         'evaluation_arm':arm, 'check_result':result, 'workload_origin':origin,
                         'check_source':'external_reported'})
    # Private identity-only index avoids rescanning raw history on every turn.
    from codex_model_router.storage.state_store import atomic_json
    import hashlib
    key = hashlib.sha256(decision_id.encode()).hexdigest()
    atomic_json(state / 'check-feedback' / (key + '.json'), {'failed': any(r.get('check_result') == 'failed' for r in previous) or result == 'failed'})


def check_feedback(state, decision_id):
    if not isinstance(decision_id, str) or not decision_id:
        return False
    import hashlib
    import json
    try:
        value = json.loads((Path(state) / 'check-feedback' / (hashlib.sha256(decision_id.encode()).hexdigest() + '.json')).read_text())
        return isinstance(value, dict) and value.get('failed') is True
    except (OSError, ValueError, TypeError):
        return False


def evaluate_checks(records):
    decisions = {}
    for r in records:
        key = r.get('decision_id')
        if not isinstance(key, str):
            continue
        row = decisions.setdefault(key, {'checks':{}, 'usage':{}, 'retries':0, 'classifier':{}})
        kind = r.get('event')
        if kind == 'decision_created':
            row['created'] = True
        elif kind == 'decision_completed':
            row['terminal'] = r.get('status')
        elif kind == 'decision_usage':
            row['usage'] = {k:v for k,v in r.items() if k in ('inputTokens','outputTokens','cachedInputTokens','reasoningOutputTokens') and type(v) in (int,float) and math.isfinite(v) and v >= 0}
        elif kind == 'native_turn_error' and r.get('will_retry') is True:
            row['retries'] += 1
        elif kind == 'engine_comparison' and r.get('engine_active') is True:
            row['classifier'][r.get('routing_engine','unknown')] = {k:v for k,v in r.items() if k in ('engine_input_tokens','engine_output_tokens','engine_latency_ms') and type(v) in (int,float) and math.isfinite(v) and v >= 0}
        elif kind == 'outcome_check':
            if r.get('check_source') != 'external_reported' or r.get('check_result') not in ('passed','failed'):
                continue
            cohort = tuple(r.get(k) for k in ('evaluation_id','workload_id','evaluation_arm','workload_origin'))
            if not all(isinstance(x,str) and x for x in cohort) or cohort[2] not in ('baseline','candidate') or cohort[3] not in ('real','synthetic'):
                continue
            if 'cohort' in row and row['cohort'] != cohort:
                row['conflict'] = True
            row['cohort'] = cohort
            check = r.get('check_id')
            if isinstance(check,str) and check:
                row['checks'][check] = r['check_result']
    cohorts = defaultdict(lambda:defaultdict(list))
    valid = 0
    for row in decisions.values():
        if row.get('created') and row.get('cohort') and row['checks'] and not row.get('conflict') and row.get('terminal') in ('completed','failed','interrupted'):
            evaluation, workload, arm, origin = row['cohort']
            cohorts[(evaluation,workload,origin)][arm].append(row)
            valid += 1
    matched = []; excluded = Counter()
    for (_, _, origin), arms in cohorts.items():
        if len(arms['baseline']) != 1 or len(arms['candidate']) != 1:
            excluded['missing_or_repeated_arm'] += 1
            continue
        baseline, candidate = arms['baseline'][0], arms['candidate'][0]
        if set(baseline['checks']) != set(candidate['checks']):
            excluded['different_check_sets'] += 1
            continue
        passed = lambda r: r['terminal'] == 'completed' and all(v == 'passed' for v in r['checks'].values())
        evidence = lambda r: {'last_native_usage':r['usage'], 'retry_notifications':r['retries'],
                              'classifier_input_tokens':sum(v.get('engine_input_tokens',0) for v in r['classifier'].values()),
                              'classifier_output_tokens':sum(v.get('engine_output_tokens',0) for v in r['classifier'].values()),
                              'classifier_metric_coverage':sum('engine_input_tokens' in v or 'engine_output_tokens' in v for v in r['classifier'].values()),
                              'classifier_active_comparisons':len(r['classifier'])}
        matched.append({'origin':origin, 'baseline_passed':passed(baseline), 'candidate_passed':passed(candidate),
                        'check_count':len(baseline['checks']), 'baseline_metrics':evidence(baseline), 'candidate_metrics':evidence(candidate)})
    return {'evidence_source':'external_reported_not_independently_attested', 'decisions_with_checks':valid,
            'matched_workloads':len(matched), 'matched_results':matched, 'excluded_cohorts':dict(excluded),
            'quality_status':'matched_descriptive' if matched else 'not_evaluated',
            'causal_savings_demonstrated':False, 'billed_cost_observed':False}
