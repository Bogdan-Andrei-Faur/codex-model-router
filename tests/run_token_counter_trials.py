"""One reserved public token-counter pilot, at most2native turns and1Jev call."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import candidate_policy as cp
from decision_engines import _run_jev, build_state
from desktop_runtime import discover
from model_catalog import DEFAULT_ROUTES
from state_store import atomic_json
from tests import token_counter_trials as grading, native_probe_profile, trial_tool_evidence, run_multifile_trials
from tests.coding_trials import sandbox_controls
from tests.smoke_native import Client

PAIRS = (('gpt-6-luna', 'high'), ('gpt-6.1-sol', 'high'))


def native_catalog():
    """Owned model/list only; no thread or inference created."""
    args = []
    for key, value in native_probe_profile.isolated_overrides().items():
        args += ['-c', key+'='+json.dumps(value)]
    client = Client([str(discover().backend), *args, 'app-server'])
    try:
        client.call('initialize', {'clientInfo': {'name': 'repository_trial_catalog', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
        client.send({'method': 'initialized', 'params': {}})
        return {m['model']: [e['reasoningEffort'] for e in m.get('supportedReasoningEfforts', [])
                            if e.get('reasoningEffort') in ('low', 'medium', 'high', 'xhigh')]
                for m in client.call('model/list', {})['data']
                if m['model'] in {p[0] for p in PAIRS} and not m.get('hidden')}
    finally:
        client.close(); client.temp.cleanup()


def safe_choice(value, choices):
    route = value.get('route'); pair = (route.get('model'), route.get('effort')) if isinstance(route, dict) else None
    valid = value.get('status') == 'ok' and pair in {(r['model'], r['effort']) for r in choices.values()}
    status = value.get('status')
    result = {'status': status if status in ('ok', 'abstained', 'invalid', 'unavailable', 'not_configured') else 'other',
              'valid_eligible_choice': valid,
              'selected_route': {'model': pair[0], 'effort': pair[1]} if valid else None,
              'eligible_model_count': len({r['model'] for r in choices.values()})}
    confidence = value.get('confidence')
    result['confidence'] = confidence if type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence <= 1 else None
    for key in ('latency_ms', 'engine_input_tokens', 'engine_output_tokens', 'engine_cached_tokens'):
        count = value.get(key)
        if type(count) is int and 0 <= count <= 10**9:
            result[key] = count
    cost = value.get('engine_provider_cost_usd')
    if type(cost) in (int, float) and math.isfinite(cost) and 0 <= cost <= 10000:
        result['provider_reported_classifier_usd'] = cost
    return result


def admissible(row):
    checks = row.get('checks'); tags = row.get('posterior_model_log_records')
    catalog = row.get('native_catalog'); model = row['requested_model']; effort = row['requested_effort']
    return (row.get('quality_admissible') is True and row.get('status') == 'finished'
        and row.get('terminal') == 'completed' and row.get('tool_trace_complete') is True
        and type(row.get('inference_requests')) is int and row['inference_requests'] == 1
        and type(row.get('denied_native_requests')) is int and row['denied_native_requests'] == 0
        and not any(row.get(k) for k in ('failure', 'cleanup_failure', 'interrupted', 'harness_invalid'))
        and isinstance(checks, dict) and set(checks) == grading.CHECKS-{'execution'}
        and all(type(v) is bool for v in checks.values())
        and type(row.get('workflow_complete')) is bool and type(row.get('output_check')) is bool
        and row['output_check'] == (all(checks.values()) and row['workflow_complete'])
        and isinstance(tags, dict) and set(tags) == {model}
        and type(tags[model]) is int and tags[model] > 0
        and isinstance(catalog, dict) and isinstance(catalog.get(model), list) and effort in catalog[model])


def design():
    case = grading.cases()[0]
    return [dict(case_id=case['id'], split=case['split'], requested_model=m, requested_effort=e, attempt=1)
            for m, e in PAIRS]


def run_trials(output, max_native=2, max_provider=1):
    if type(max_native) is not int or max_native != 2 or type(max_provider) is not int or max_provider != 1:
        raise ValueError('fixed_repository_quota')
    data = grading.manifest(); case = data['cases'][0]; planned = design()
    controls = sandbox_controls()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    artifacts = {'runner': Path(__file__), 'validator': Path(grading.__file__),
                 'native_runner': Path(run_multifile_trials.__file__),
                 'tool_evidence': Path(trial_tool_evidence.__file__),
                 'profile': Path(native_probe_profile.__file__),
                 'candidate_policy': ROOT/'candidate_policy.py', 'jev_engine': ROOT/'decision_engines.py',
                 'workspace': Path(grading.base.__file__), 'source_validator': ROOT/'tests/coding_trials.py'}
    report = {'schema': 'repository-token-trials/1', 'case_sha256': grading.CASE_HASH,
              'grader_sha256': grading.GRADER_HASH, 'module_loader_sha256': grading.base.GRADER_HASH,
              'origin': data['origin'], 'origin_scope': data['origin_scope'],
              'max_native_turns': max_native, 'max_provider_calls': max_provider,
              'planned_turns': planned, 'design_sha256': hashlib.sha256(json.dumps(planned, sort_keys=True).encode()).hexdigest(),
              'artifact_hashes': {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in artifacts.items()},
              'sandbox_controls': controls, 'attempts': [], 'provider_attempts': [],
              'policy_activation_eligible': False, 'complete_native_cost': 'unknown',
              'per_response_model_effort_identity': 'not_confirmed'}
    atomic_json(output/'report.json', report)
    try:
        catalog = native_catalog()
        if any(e not in catalog.get(m, []) for m, e in PAIRS):
            raise ValueError('catalog_pair_missing')
        assessment = cp.profile(case['request'])
        if assessment['work_class'] != 'bounded':
            raise ValueError('bounded_eligibility_required')
        choices = {k: r for k, r in cp.candidates(DEFAULT_ROUTES, catalog, assessment).items()
                   if (r['model'], r['effort']) in PAIRS}
        if {(r['model'], r['effort']) for r in choices.values()} != set(PAIRS):
            raise ValueError('eligible_pair_missing')
        report.update(native_catalog=catalog, eligible_choices=[{'model': r['model'], 'effort': r['effort']}
                                                               for r in choices.values()], work_class='bounded',
                      choice_scope='two_catalog_supported_high_routes_not_all_eligible_efforts')
    except Exception:
        report.update(campaign_stopped=True, preflight_failure='catalog_or_eligibility_unavailable')
        atomic_json(output/'report.json', report)
        return report
    # The classifier's intent and fixed full design precede provider execution
    # and ALL native answers. Missing configuration still consumes this slot.
    intent = {'case_id': case['id'], 'status': 'intent', 'before_native_outcomes': True}
    report['provider_attempts'].append(intent); atomic_json(output/'report.json', report)
    try:
        config = json.loads((ROOT/'config.local.json').read_text(encoding='utf-8-sig'))
        state = build_state(case['request'], {'present': False, 'count': 0}, None, None, False)
        state.update(candidate_policy_version=9, work_context=assessment)
        value = _run_jev(config, ROOT/'state', state, choices)
    except Exception:
        value = {'status': 'unavailable'}
    intent.update(safe_choice(value, choices)); atomic_json(output/'report.json', report)
    stop = False
    for spec in planned:
        if stop:
            break
        arm = dict(spec, status='intent')
        report['attempts'].append(arm); atomic_json(output/'report.json', report)
        workspace = None
        try:
            workspace = trial_tool_evidence.Workspace(case, grading.grade, grading.CHECKS)
            arm.update(run_multifile_trials.run_arm(case, spec['requested_model'], effort=spec['requested_effort'],
                                                   workspace=workspace, dynamic_specs=grading.tools(case)))
        except KeyboardInterrupt:
            arm.update(interrupted=True, failure='owned_harness_interrupted', output_check=False)
        except Exception:
            arm.update(failure='owned_harness_failure', output_check=False)
        finally:
            if workspace:
                try:
                    workspace.close()
                except Exception:
                    arm['cleanup_failure'] = 'owned_cleanup_failure'
        arm['quality_admissible'] = bool(admissible(arm))
        stop = not arm['quality_admissible']
        atomic_json(output/'report.json', report)
        print(json.dumps({'model': spec['requested_model'], 'passed': arm.get('output_check') is True,
                          'quality_admissible': arm['quality_admissible'], 'campaign_stopped': stop}), flush=True)
    rows = report['attempts']
    matches = [r for r in rows if intent.get('selected_route') == {'model': r['requested_model'], 'effort': r['requested_effort']}]
    intent['measured_exercise_pass'] = matches[0]['output_check'] if len(matches) == 1 and matches[0]['quality_admissible'] else None
    intent['measurement_scope'] = 'fixed_heldout_snapshot_requested_route_not_optimal_choice_or_identity_proof'
    report.update(campaign_stopped=stop, complete_design=len(rows) == len(planned) and not stop,
                  native_turn_requests=sum(r['inference_requests'] if type(r.get('inference_requests')) is int
                                           and r['inference_requests'] in (0, 1) else 1 for r in rows),
                  quality_attempts=sum(r['quality_admissible'] for r in rows),
                  passed=sum(r['quality_admissible'] and r['output_check'] for r in rows),
                  provider_attempt_slots=len(report['provider_attempts']), calibrated_threshold=None)
    atomic_json(output/'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true'); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({'planned_turns': design(), 'max_native': 2, 'max_provider': 1,
                          'new_native_calls': 0, 'new_provider_calls': 0}))
        return 0
    if not args.output or args.output.exists():
        parser.error('requires new output directory')
    report = run_trials(args.output)
    print(json.dumps({k: report.get(k) for k in ('native_turn_requests', 'provider_attempt_slots', 'passed', 'quality_attempts', 'complete_design', 'campaign_stopped')}))
    return 1 if report.get('campaign_stopped') else 0


if __name__ == '__main__':
    sys.exit(main())
