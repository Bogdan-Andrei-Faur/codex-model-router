"""Offline, frozen campaign inventory. No provider calls or activation receipt.

Count distinct fixture identities separately from executions, repetitions and
instrument validation. A reported pass is not a model identity or cost proof.
Only authored labels, counters and allowlisted metrics leave this evaluator.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from state_store import atomic_json
from tests.evaluate_jev_trials import link_measured
from tests.probe_inference_identity import PROBE_MODELS

LABEL = re.compile(r'[a-z0-9][a-z0-9_.-]{0,63}\Z')
HASH = re.compile(r'[a-f0-9]{64}\Z')
TOKENS = ('inputTokens', 'cachedInputTokens', 'outputTokens')
PURPOSES = ('comparison', 'instrument', 'invalid_harness')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounded_int(value):
    return type(value) is int and 0 <= value <= 10**12


def frozen(root, ref):
    root = Path(root).resolve()
    path = ref.get('path')
    if (not isinstance(path, str) or Path(path).is_absolute()
            or '..' in Path(path).parts or not path.startswith('state/')
            or not isinstance(ref.get('sha256'), str) or not HASH.fullmatch(ref['sha256'])):
        raise ValueError('invalid_frozen_reference')
    target = root / path
    if any((root / Path(*Path(path).parts[:i])).is_symlink()
           for i in range(1, len(Path(path).parts) + 1)):
        raise ValueError('unsafe_frozen_reference')
    data = target.read_bytes()
    if digest(data) != ref['sha256']:
        raise ValueError('frozen_report_mismatch')
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError('invalid_frozen_report')
    return value


def result(row, spec):
    """Typed final external outcome; complete negatives remain negatives."""
    checks = row.get('checks')
    expected = spec['checks'][row['case_id']]
    if (not isinstance(checks, dict) or set(checks) != set(expected)
            or not all(type(v) is bool for v in checks.values())
            or checks.get('execution') is False
            or type(row.get('output_check')) is not bool):
        return None
    legacy = spec['schema'] == 'isolated-coding-trials/1'
    if (row.get('terminal') != 'completed' or type(row.get('attempt')) is not int
            or row['attempt'] != 1 or type(row.get('inference_requests')) is not int
            or row['inference_requests'] != 1
            or any(row.get(k) for k in ('failure', 'cleanup_failure', 'interrupted', 'harness_invalid'))):
        return None
    if not legacy and (row.get('status') != 'finished'
            or row.get('quality_admissible') is not True
            or type(row.get('denied_native_requests')) is not int
            or row['denied_native_requests'] != 0
            or type(row.get('workflow_complete')) is not bool):
        return None
    workflow = True if legacy else row['workflow_complete']
    if row['output_check'] != (all(checks.values()) and workflow):
        return None
    return row['output_check']


def inventory(root, plan):
    if (not isinstance(plan, dict) or plan.get('schema') != 'evidence-inventory-plan/1'
            or not isinstance(plan.get('campaigns'), list) or not plan['campaigns']):
        raise ValueError('invalid_inventory_plan')
    ids = set(); hashes = set(); fingerprints = set(); problems = set()
    campaigns = []; groups = defaultdict(Counter); by_route = defaultdict(Counter)
    loaded = {}
    for spec in plan['campaigns']:
        if (spec.get('purpose') not in PURPOSES
                or not isinstance(spec.get('id'), str) or not LABEL.fullmatch(spec['id'])
                or spec['id'] in ids or spec.get('sha256') in hashes
                or not isinstance(spec.get('checks'), dict) or not spec['checks']
                or any(not isinstance(k, str) or not LABEL.fullmatch(k) or not isinstance(v, list) or not v
                       or len(set(v)) != len(v)
                       or any(not isinstance(x, str) or not LABEL.fullmatch(x) for x in v)
                       for k, v in spec['checks'].items())):
            raise ValueError('invalid_campaign_membership')
        ids.add(spec['id']); hashes.add(spec['sha256'])
        report = frozen(root, spec); loaded[spec['id']] = report
        if (report.get('schema') != spec.get('schema')
                or report.get('case_sha256') != spec.get('case_sha256')
                or report.get('grader_sha256') != spec.get('grader_sha256')
                or not isinstance(spec.get('case_sha256'), str)
                or not HASH.fullmatch(spec['case_sha256'])
                or not isinstance(report.get('attempts'), list) or not report['attempts']):
            raise ValueError('invalid_campaign_origin')
        purpose = spec['purpose']
        if purpose == 'invalid_harness' and spec.get('reviewed_exclusion') not in (
                'initial_profile_did_not_enable_required_code_mode', 'allowed_paths_not_exposed'):
            raise ValueError('missing_reviewed_exclusion')
        if spec.get('exclusion_audit'):
            audit = frozen(root, spec['exclusion_audit'])
            if (purpose != 'invalid_harness' or audit.get('quality_admissible') is not False
                    or audit.get('original_report_sha256') != spec['sha256']):
                raise ValueError('invalid_exclusion_audit')
        stats = Counter(attempts=0, native_requests=0, preflight_attempts=0, unknown_native_requests=0,
                        measured_outcomes=0, passed=0, failed=0, unknown_outcomes=0,
                        token_covered_requests=0, response_usage_reconciled_requests=0,
                        strict_model_identity_requests=0)
        fixture_ids = set()
        for row in report['attempts']:
            if (not isinstance(row, dict) or row.get('case_id') not in spec['checks']
                    or row.get('requested_model') not in PROBE_MODELS
                    or row.get('requested_effort') not in ('low', 'medium', 'high', 'xhigh')):
                raise ValueError('invalid_attempt_membership')
            # Cumulative historical snapshots may contain the same executions.
            # Reject overlap; never count them as independent repetitions.
            fingerprint = digest(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())
            if fingerprint in fingerprints:
                raise ValueError('overlapping_execution_records')
            fingerprints.add(fingerprint)
            stats['attempts'] += 1
            requests = row.get('inference_requests')
            if type(requests) is int and requests in (0, 1):
                stats['native_requests'] += requests
                stats['preflight_attempts'] += requests == 0
            else:
                stats['unknown_native_requests'] += 1
            if requests == 1 and type(requests) is int:
                tokens = row.get('native_thread_total_tokens')
                if (isinstance(tokens, dict) and all(bounded_int(tokens.get(k)) for k in TOKENS)
                        and tokens['cachedInputTokens'] <= tokens['inputTokens']):
                    stats['token_covered_requests'] += 1
                    for key in TOKENS:
                        stats[key] += tokens[key]
                    raw = row.get('native_raw_evidence')
                    if (isinstance(raw, dict) and row.get('raw_usage_matches_native_total') is True
                            and isinstance(raw.get('counts'), dict)
                            and type(raw['counts'].get('joined')) is int and raw['counts']['joined'] > 0
                            and raw.get('responses_missing_usage') == 0
                            and type(raw.get('responses_missing_usage')) is int
                            and isinstance(raw.get('response_tokens_sum'), dict)
                            and all(type(raw['response_tokens_sum'].get(k)) is int
                                    and raw['response_tokens_sum'][k] == tokens[k] for k in TOKENS)):
                        stats['response_usage_reconciled_requests'] += 1
                # No supported per-response effort/model attestation is present
                # in these schemas. A matching OTel tag never changes this zero.
            outcome = result(row, spec) if purpose == 'comparison' else None
            stats['unknown_outcomes'] += outcome is None
            stats['measured_outcomes'] += type(outcome) is bool
            stats['passed'] += outcome is True
            stats['failed'] += outcome is False
            if type(outcome) is bool:
                fixture = (spec['case_sha256'], row['case_id'])
                problems.add(fixture); fixture_ids.add(fixture)
                route = (row['requested_model'], row['requested_effort'])
                by_route[route]['measured_outcomes'] += 1
                by_route[route]['passed'] += outcome is True
                by_route[route]['failed'] += outcome is False
        count = dict(stats)
        count['distinct_measured_fixtures'] = len(fixture_ids)
        campaigns.append(dict(id=spec['id'], purpose=purpose, report_sha256=spec['sha256'], **count))
        groups[purpose].update(stats)
    jev = plan.get('jev')
    if not isinstance(jev, dict) or jev.get('native_campaign') not in loaded:
        raise ValueError('invalid_jev_origin')
    # Recompute the strict joins instead of trusting cached measured booleans.
    linked = link_measured(frozen(root, jev), loaded[jev['native_campaign']])
    rows = linked['attempts']
    choices = [r for r in rows if type(r.get('eligible_model_count')) is int
               and r['eligible_model_count'] > 1 and r.get('independent_model_judgment_possible') is True]
    multi_measured = [r for r in choices if type(r.get('measured_exercise_pass')) is bool]
    return {'schema': 'evidence-inventory/1', 'scope': 'explicit_frozen_campaigns_not_all_desktop_history',
            'evaluator_sha256': digest(Path(__file__).read_bytes()),
            'inventory_plan_sha256': digest(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()),
            'campaigns': campaigns, 'by_purpose': {k: dict(v) for k, v in sorted(groups.items())},
            'distinct_measured_fixtures': len(problems),
            'fixture_identity_basis': 'frozen_manifest_digest_and_case_id_not_statistical_independence',
            'by_requested_route': [dict(requested_model=m, requested_effort=e, **dict(v))
                                   for (m, e), v in sorted(by_route.items())],
            'jev': {'observations': len(rows), 'multiple_model_choices': len(choices),
                    'linked_outcomes': sum(type(r.get('measured_exercise_pass')) is bool for r in rows),
                    'linked_failures': sum(r.get('measured_exercise_pass') is False for r in rows),
                    'multiple_model_linked_outcomes': len(multi_measured),
                    'multiple_model_linked_failures': sum(r['measured_exercise_pass'] is False for r in multi_measured),
                    'confidence_threshold': None, 'calibration_ready': False},
            'new_native_calls': 0, 'new_provider_calls': 0, 'policy_activation_eligible': False,
            'strict_model_effort_identity': 'not_attested_by_these_schemas',
            'complete_native_cost': 'unknown', 'billed_savings': 'not_demonstrated',
            'source_payloads_copied': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/'tests/evidence_inventory_plan.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('requires a new output file')
    try:
        report = inventory(ROOT, json.loads(args.plan.read_text()))
    except (ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'status': 'invalid_frozen_inventory', 'native_calls': 0, 'provider_calls': 0}))
        return 1
    atomic_json(args.output, report)
    print(json.dumps({k: report[k] for k in ('distinct_measured_fixtures', 'by_purpose', 'jev', 'new_native_calls', 'new_provider_calls')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
