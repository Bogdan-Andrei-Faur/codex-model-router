"""Content-free outcome coverage report. Never infers quality from completion."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from state_store import read_records
from outcome_evaluation import evaluate_checks


def evaluate(records):
    records = list(records)
    decisions = {}
    for event in records:
        key = event.get('decision_id')
        if not isinstance(key, str): continue
        row = decisions.setdefault(key, {})
        kind = event.get('event')
        if kind == 'decision_created': row['created'] = True
        if kind == 'decision_routed':
            engine = event.get('routing_engine')
            row['engine'] = engine if engine in ('rules', 'jev') else 'unknown'
        if kind == 'decision_completed':
            status = event.get('status')
            row['status'] = status if status in ('completed', 'failed', 'interrupted') else 'unknown'
        if kind == 'decision_quality':
            for field in ('quality', 'model_quality', 'effort_quality'):
                if field in event:
                    value = event[field]
                    row[field] = value if value in ('adequate', 'insufficient', 'excessive') else None
        if kind == 'inference_observed' and event.get('evidence_confidence') == 'confirmed':
            row['confirmed_inference'] = True
    groups = {}
    for engine in ('rules', 'jev', 'unknown'):
        rows = [r for r in decisions.values() if r.get('created') and r.get('engine', 'unknown') == engine]
        if not rows: continue
        groups[engine] = {'decisions': len(rows),
            'terminal_status': dict(Counter(r.get('status', 'unclosed') for r in rows)),
            'quality_ratings': dict(Counter(r['quality'] for r in rows if r.get('quality'))),
            'model_ratings': dict(Counter(r['model_quality'] for r in rows if r.get('model_quality'))),
            'effort_ratings': dict(Counter(r['effort_quality'] for r in rows if r.get('effort_quality'))),
            'confirmed_inference_decisions': sum(bool(r.get('confirmed_inference')) for r in rows)}
    rated = sum(sum(g['quality_ratings'].values()) for g in groups.values())
    return {'groups': groups, 'quality_status': 'descriptive_only' if rated else 'not_evaluated',
            'objective_checks': evaluate_checks(records),
            'causal_savings_demonstrated': False,
            'limitations': ['Completion is not correctness.', 'Ratings are subjective and selected, not a controlled comparison.',
                            'Mixed-model turn tokens cannot establish per-model cost or quota savings.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', type=Path, default=Path(__file__).resolve().parents[1]/'state/history.jsonl')
    args = parser.parse_args()
    print(json.dumps(evaluate(read_records(args.history)), indent=2))
