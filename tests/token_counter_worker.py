"""Independent explicit normalization vectors; trusted Seatbelt worker."""
import copy
import json
from pathlib import Path
import resource
import runpy
import sys

helpers = runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact = helpers['exact']; load_modules = helpers['load_modules']


def check(sources):
    module = load_modules(sources)['counter']
    groups = {
        'valid_counters': [(0, 0), (1, 1), (1000000000, 1000000000),
            (0.0, 0), (42.0, 42), (1000000000.0, 1000000000),
            ('0', 0), ('0000', 0), (' +42 ', 42), ('\t1000000000\n', 1000000000)],
        'malformed_unknown': [(True, None), (False, None), (None, None),
            (1.2, None), (-1, None), (-0.1, None), (1000000001, None), (1000000001.0, None),
            ('', None), (' ', None), ('+', None), ('-0', None), ('-1', None),
            ('1.0', None), ('1e2', None), ('1_000', None), ('1 0', None), ('１２', None),
            ('١٢', None), ('²', None), ('1000000001', None), ('0'*11, None), ('9'*5000, None),
            ({'tokens': 8}, None), ([8], None), ((8,), None),
            (float('inf'), None), (float('-inf'), None), (float('nan'), None)],
    }
    # Broader type/boundary checks, all part of this single held-out task.
    groups['valid_counters'] += [(n, n) for n in range(30)]
    groups['valid_counters'] += [(str(n), n) for n in range(30)]
    groups['malformed_unknown'] += [(n/2, None) for n in range(1, 30, 2)]
    checks = {key: True for key in groups}; checks['no_mutation'] = True
    for key, rows in groups.items():
        for value, expected in rows:
            before = copy.deepcopy(value)
            try:
                checks[key] &= exact(module.token_count(value), expected)
            except BaseException:
                checks[key] = False
            # NaN equality is deliberately not a mutation oracle.
            if isinstance(value, (dict, list, tuple)):
                checks['no_mutation'] &= value == before
    return {key: bool(value) for key, value in checks.items()}


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        sources = json.loads(open(sys.argv[1], encoding='utf-8').read())
        print(json.dumps(check(sources)))
    except BaseException:
        print(json.dumps({'execution': False}))


if __name__ == '__main__':
    main()
