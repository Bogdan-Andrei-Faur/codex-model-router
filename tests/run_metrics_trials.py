"""Fixed allocation: four isolated turns and two classifier calls, no retries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import candidate_policy as cp
import inference_telemetry as otel
from decision_engines import _run_jev, build_state
from model_catalog import DEFAULT_ROUTES
from state_store import atomic_json
from tests import metrics_trials as grading, run_multifile_trials as native, trial_tool_evidence
from tests.coding_trials import sandbox_controls
from tests.run_token_counter_trials import PAIRS, native_catalog, safe_choice


def admissible(row):
    checks = row.get('checks'); tags = row.get('posterior_model_log_records')
    return bool(row.get('quality_admissible') is True and row.get('status') == 'finished'
        and row.get('terminal') == 'completed' and row.get('tool_trace_complete') is True
        and type(row.get('inference_requests')) is int and row['inference_requests'] == 1
        and type(row.get('denied_native_requests')) is int and row['denied_native_requests'] == 0
        and not any(row.get(k) for k in ('failure', 'cleanup_failure', 'interrupted', 'harness_invalid'))
        and isinstance(checks, dict) and set(checks) == grading.CHECKS-{'execution'}
        and all(type(v) is bool for v in checks.values())
        and type(row.get('workflow_complete')) is bool and type(row.get('output_check')) is bool
        and row['output_check'] == (all(checks.values()) and row['workflow_complete'])
        and isinstance(tags, dict) and set(tags) == {row['requested_model']}
        and type(tags[row['requested_model']]) is int and tags[row['requested_model']] > 0
        and row['requested_effort'] in row.get('native_catalog', {}).get(row['requested_model'], []))


def run(output, previous=None, identity_probe=None):
    data = grading.manifest(); controls = sandbox_controls()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    design = [dict(case_id=case['id'], requested_model=m, requested_effort=e, attempt=1)
              for index, case in enumerate(data['cases']) for m, e in (PAIRS if index == 0 else PAIRS[::-1])]
    artifacts = [Path(__file__), Path(grading.__file__), Path(native.__file__),
                 Path(trial_tool_evidence.__file__), ROOT/'tests/native_probe_profile.py',
                 ROOT/'candidate_policy.py', ROOT/'decision_engines.py', ROOT/'inference_telemetry.py']
    report = dict(schema='metrics-repository-trials/1', case_sha256=grading.CASE_HASH,
                  grader_sha256=grading.GRADER_HASH, origin=data['origin'], origin_scope=data['origin_scope'],
                  artifact_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
                  design=design, sandbox_controls=controls, max_native_turns=4, max_provider_calls=2,
                  attempts=[], provider_attempts=[], policy_activation_eligible=False,
                  per_response_model_effort_identity='not_confirmed', complete_native_cost='unknown')
    if previous:
        prior = json.loads(previous.read_text()); probe = json.loads(identity_probe.read_text())
        if (prior.get('case_sha256') != grading.CASE_HASH or prior.get('grader_sha256') != grading.GRADER_HASH
                or prior.get('native_turn_requests') != 1 or prior.get('quality_attempts') != 0
                or prior.get('provider_attempt_slots') != 2 or probe.get('inference_requests') != 1
                or probe.get('live') is not True or probe.get('output_check') is not True
                or len(prior.get('provider_attempts', [])) != 2):
            raise ValueError('recovery_allocation_invalid')
        # One explicit recovery allocation only. The original receipt remains
        # immutable; no additional classifier call or invisible native retry.
        with (previous.parent/'recovery-reserved.json').open('x') as marker:
            json.dump({'output': output.name, 'max_remaining_native_turns': 4, 'new_provider_calls': 0}, marker)
        report.update(previous_report_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
                      identity_probe_sha256=hashlib.sha256(identity_probe.read_bytes()).hexdigest(),
                      prior_native_turns_consumed=2, max_total_native_turns=6,
                      new_provider_calls=0, provider_choices_reused=True,
                      provider_attempts=prior['provider_attempts'])
    atomic_json(output/'report.json', report)
    catalog = native_catalog()
    if any(e not in catalog.get(m, []) for m, e in PAIRS):
        report.update(campaign_stopped=True, preflight_failure='catalog_pair_missing')
        atomic_json(output/'report.json', report); return report
    # Both classifier choices precede every model outcome.
    for case in ([] if previous else data['cases']):
        assessment = cp.profile(case['request'])
        if assessment['work_class'] != 'bounded':
            report.update(campaign_stopped=True, preflight_failure='bounded_eligibility_required')
            atomic_json(output/'report.json', report); return report
        choices = {k: r for k, r in cp.candidates(DEFAULT_ROUTES, catalog, assessment).items()
                   if (r['model'], r['effort']) in PAIRS}
        if {(r['model'], r['effort']) for r in choices.values()} != set(PAIRS):
            raise ValueError('eligible_pair_missing')
        intent = dict(case_id=case['id'], status='intent', before_native_outcomes=True)
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
    for spec in design:
        if stop:
            break
        case = next(c for c in data['cases'] if c['id'] == spec['case_id'])
        arm = dict(spec, status='intent'); report['attempts'].append(arm)
        atomic_json(output/'report.json', report)
        workspace = None
        shapes = native.IdentityShapes(); original = otel.safe_records
        def inspect(payload, health=None):
            shapes.inspect(payload)
            yield from original(payload, health)
        try:
            workspace = trial_tool_evidence.Workspace(case, grading.grade, grading.CHECKS)
            with patch.object(native, 'IdentityShapes', lambda: shapes), patch.object(otel, 'safe_records', inspect):
                arm.update(native.run_arm(case, spec['requested_model'], effort=spec['requested_effort'],
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
        arm['quality_admissible'] = admissible(arm)
        stop = not arm['quality_admissible']
        atomic_json(output/'report.json', report)
        print(json.dumps({k: arm.get(k) for k in ('case_id', 'requested_model', 'output_check', 'quality_admissible')}), flush=True)
    for choice in report['provider_attempts']:
        match = [r for r in report['attempts'] if r['case_id'] == choice['case_id'] and
                 choice.get('selected_route') == {'model': r['requested_model'], 'effort': r['requested_effort']}]
        choice['measured_exercise_pass'] = match[0]['output_check'] if len(match) == 1 and match[0]['quality_admissible'] else None
    report.update(complete_design=len(report['attempts']) == 4 and not stop, campaign_stopped=stop,
                  native_turn_requests=sum(r.get('inference_requests', 1) for r in report['attempts']),
                  quality_attempts=sum(r['quality_admissible'] for r in report['attempts']),
                  passed=sum(r['quality_admissible'] and r.get('output_check') is True for r in report['attempts']),
                  provider_attempt_slots=len(report['provider_attempts']), calibrated_threshold=None)
    atomic_json(output/'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true'); parser.add_argument('--output', type=Path)
    parser.add_argument('--previous', type=Path); parser.add_argument('--identity-probe', type=Path)
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({'max_native_turns': 4, 'max_provider_calls': 2, 'new_calls': 0}))
    elif not args.output or args.output.exists() or bool(args.previous) != bool(args.identity_probe):
        parser.error('requires new output directory')
    else:
        report = run(args.output, args.previous, args.identity_probe)
        print(json.dumps({k: report.get(k) for k in ('complete_design', 'quality_attempts', 'passed', 'native_turn_requests', 'provider_attempt_slots', 'preflight_failure')}))
        sys.exit(int(report.get('campaign_stopped', False)))
