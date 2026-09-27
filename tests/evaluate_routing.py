"""Versioned synthetic conversation evaluation; no network or persisted content."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routing import DEFAULT_ROUTES, EFFORTS, TIERS, select_route_details
from workload import effective_context, merge_contract, response_summary
from decision_engines import candidate_routes
from build_identity import identity, POLICY_VERSION


def evaluate():
    corpus = json.loads(Path(__file__).with_name('routing_cases.json').read_text(encoding='utf-8'))
    catalog = {route['model']: set(EFFORTS) for route in DEFAULT_ROUTES.values()}
    results = []
    for case in corpus['cases']:
        row = {}
        for response in case.get('assistant', []):
            row['response_context'] = response_summary(response)
            row['task_contract'] = merge_contract(row.get('task_contract'), row['response_context'])
        route, policy = select_route_details(case['prompt'], DEFAULT_ROUTES, attachments=case.get('attachments', False), response_context=effective_context(row))
        tier = next(key for key, value in DEFAULT_ROUTES.items() if value['model'] == route['model'])
        passed = (TIERS.index(case['min_model']) <= TIERS.index(tier) <= TIERS.index(case['max_model']) and
                  EFFORTS.index(case['min_effort']) <= EFFORTS.index(route['effort']) <= EFFORTS.index(case['max_effort']))
        candidates = candidate_routes(DEFAULT_ROUTES, catalog, policy)
        # Both engines must respect the same lower bounds for substantive work.
        if policy.get('quality_floor'):
            passed &= all(TIERS.index(r['tier']) >= TIERS.index(policy['quality_floor']) and
                          EFFORTS.index(r['effort']) >= EFFORTS.index(policy['min_effort']) for r in candidates.values())
        if policy.get('quality_ceiling'):
            passed &= all(TIERS.index(r['tier']) <= TIERS.index(policy['quality_ceiling']) for r in candidates.values())
        if 'candidate_tiers' in case:
            passed &= {r['tier'] for r in candidates.values()} == set(case['candidate_tiers'])
        results.append({'case': case['id'], 'passed': bool(passed), 'model': tier, 'effort': route['effort']})
    version, build = identity(Path(__file__).resolve().parents[1])
    return {'corpus_version': corpus['schema'], 'product_version': version, 'build_id': build,
            'policy_version': POLICY_VERSION, 'passed': sum(r['passed'] for r in results), 'total': len(results), 'cases': results}


if __name__ == '__main__':
    report = evaluate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(report['passed'] != report['total'])
