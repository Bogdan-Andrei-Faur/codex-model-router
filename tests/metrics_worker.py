"""Explicit external vectors, executed only in the existing Seatbelt grader."""
import copy
import json
from pathlib import Path
import resource
import runpy
import sys

helpers = runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact = helpers['exact']


def checks(case, sources):
    module = helpers['load_modules'](sources)['subject']
    result = {'identity_or_provenance': True, 'boundary_cases': True, 'no_mutation': True}
    if case == 'exact-attribution':
        row = dict(turn_id='turn-one', phase_status='active', accepted_model='gpt-6.1-sol',
                   accepted_effort='high', decision_started_at=10)
        record = dict(thread_id='thread-one', turn_id='turn-one', model='gpt-6-astra', effort='xhigh', timestamp=20)
        rows = [(record, {'thread-one': row}, 30, ('thread-one', True, None)),
                (dict(record, turn_id=None), {'thread-one': row}, 30, (None, False, 'model_mismatch')),
                (dict(record, model='gpt-6.1-sol', effort='high', turn_id=None), {'thread-one': row}, 30, ('thread-one', False, None)),
                (dict(record, turn_id='turn-other'), {'thread-one': row}, 30, (None, False, 'turn_mismatch')),
                (dict(record, thread_id='thread-other'), {'thread-one': row}, 30, (None, False, 'unknown_thread')),
                (record, {'thread-one': dict(row, phase_status='inactive')}, 30, (None, False, 'inactive')),
                (record, {'thread-one': dict(row, phase_status='completed', completed_at=14)}, 30, (None, False, 'stale')),
                (record, {'thread-one': dict(row, phase_status='completed', completed_at=15)}, 30, ('thread-one', True, None)),
                (dict(record, timestamp=9), {'thread-one': row}, 30, (None, False, 'stale')),
                (dict(record, timestamp=35), {'thread-one': row}, 30, ('thread-one', True, None)),
                (dict(record, timestamp=36), {'thread-one': row}, 30, (None, False, 'invalid_timestamp')),
                (dict(record, timestamp=True), {'thread-one': row}, 30, (None, False, 'invalid_timestamp')),
                (dict(record, timestamp=None), {'thread-one': dict(row, phase_accepted_at=15)}, 30, ('thread-one', False, None)),
                (record, {'thread-one': dict(row, phase_accepted_at=21)}, 30, (None, False, 'stale')),
                (dict(model='gpt-6.1-sol', effort='high'), {'a': row, 'b': dict(row)}, 30, (None, False, 'ambiguous'))]
        for index, (event, threads, now, expected) in enumerate(rows):
            before = copy.deepcopy((event, threads))
            try:
                candidate, confirmed, rejection = module.attribute(event, threads, now)
                actual = (candidate[0] if candidate else None, confirmed, rejection)
                valid = exact(actual, expected) and (candidate is None or candidate[1] is threads[candidate[0]])
            except BaseException:
                valid = False
            result['identity_or_provenance' if index < 3 else 'boundary_cases'] &= valid
            result['no_mutation'] &= (event, threads) == before
    else:
        def expected(risk=False, legacy=False, failures=0, feedback=None, remaining='critical'):
            return dict(version=9, remaining_class=remaining, risk_active=risk, legacy_uncertain=legacy,
                        quality_failures=failures, feedback_id=feedback)
        legacy = dict(work_class='critical', risk_active=False, legacy_uncertain=True, failure_class='none', new_task=False)
        active = dict(legacy, risk_active=True, legacy_uncertain=False)
        failed = dict(legacy, failure_class='external_check')
        rows = [({}, legacy, None, expected(legacy=True)),
                ({}, active, None, expected(risk=True)),
                ({}, dict(active, legacy_uncertain=True), None, expected(risk=True, legacy=True)),
                ({'quality_failures': 2, 'feedback_id': 'old'}, failed, 'new', expected(legacy=True, failures=3, feedback='new')),
                ({'quality_failures': 2, 'feedback_id': 'old'}, failed, 'old', expected(legacy=True, failures=2, feedback='old')),
                ({'quality_failures': 100}, failed, 'new', expected(legacy=True, failures=100, feedback='new')),
                ({'quality_failures': True}, failed, 'new', expected(legacy=True, failures=1, feedback='new')),
                ({'quality_failures': -2}, failed, None, expected(legacy=True)),
                ({'quality_failures': 101}, legacy, None, expected(legacy=True)),
                ({'quality_failures': '2'}, legacy, None, expected(legacy=True)),
                ({'quality_failures': 2.0}, legacy, None, expected(legacy=True)),
                ({'quality_failures': 4, 'feedback_id': 'old'}, dict(legacy, new_task=True), None, expected(legacy=True)),
                ({'quality_failures': 4, 'feedback_id': 'old'}, dict(failed, new_task=True), 'new', expected(legacy=True, failures=1, feedback='new')),
                ({'quality_failures': 4}, dict(legacy, failure_class='infrastructure'), 'new', expected(legacy=True, failures=4, feedback='new')),
                (None, dict(work_class='bounded', risk_active=False, failure_class='none'), None, expected(remaining='bounded'))]
        for index, (old, assessment, feedback, wanted) in enumerate(rows):
            before = copy.deepcopy((old, assessment))
            try:
                valid = exact(module.next_contract(old, assessment, feedback), wanted)
            except BaseException:
                valid = False
            result['identity_or_provenance' if index < 3 else 'boundary_cases'] &= valid
            result['no_mutation'] &= (old, assessment) == before
    return {key: bool(value) for key, value in result.items()}


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        print(json.dumps(checks(sys.argv[1], json.loads(open(sys.argv[2], encoding='utf-8').read()))))
    except BaseException:
        print(json.dumps({'execution': False}))
