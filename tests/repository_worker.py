"""Trusted external oracle for a fixed repository function; Seatbelt required."""
import copy
import itertools
import json
from pathlib import Path
import resource
import runpy
import sys

helpers = runpy.run_path(str(Path(__file__).with_name('multifile_worker.py')))
exact = helpers['exact']; load_modules = helpers['load_modules']


def check(sources, alternatives):
    alternatives = {key: tuple(value) for key, value in alternatives.items()}
    modules = load_modules(sources)
    module = modules['catalog']
    frozen = copy.deepcopy(alternatives)
    module.deepcopy = copy.deepcopy
    module.ALTERNATIVES = copy.deepcopy(alternatives)
    checks = {'compatible_fallback': True, 'priority_and_original': True,
              'no_mutation': True, 'deep_copy_and_fields': True}
    # Explicit support/presence vectors determine expected selection. All
    # combinations are checks within ONE fixture, not independent workloads.
    for original, backups in alternatives.items():
        names = [original, *backups]
        for effort in ('low', 'medium', 'high', 'xhigh'):
            for values in itertools.product(range(5), repeat=len(names)):
                catalog = {}
                for name, status in zip(names, values):
                    if status:
                        catalog[name] = {effort} if status == 1 else set() if status == 2 else effort if status == 3 else None
                if values[0]:
                    expected_model = original
                else:
                    indices = [i for i in range(1, len(names)) if values[i] == 1]
                    expected_model = names[min(indices)] if indices else original
                routes = {'test': {'model': original, 'effort': effort, 'extra': {'values': [1, 2]}}}
                before = copy.deepcopy((routes, catalog))
                expected = copy.deepcopy(routes); expected['test']['model'] = expected_model
                try:
                    result = module.available_routes(routes, catalog)
                    checks['compatible_fallback'] &= exact(result, expected)
                    if values[0] or len([v for v in values[1:] if v == 1]) > 1:
                        checks['priority_and_original'] &= exact(result, expected)
                    checks['deep_copy_and_fields'] &= (result is not routes and result['test'] is not routes['test']
                        and result['test']['extra'] is not routes['test']['extra']
                        and result['test']['extra']['values'] is not routes['test']['extra']['values'])
                    result['test']['extra']['values'].append(3)
                except BaseException:
                    checks['compatible_fallback'] = False
                    checks['deep_copy_and_fields'] = False
                checks['no_mutation'] &= (routes, catalog) == before and module.ALTERNATIVES == frozen
    # Native sets, explicit lists/tuples, malformed dicts, custom models, and
    # multiple tiers. No current price or model-quality claims are involved.
    cases = [({}, {}, {}),
        ({'simple': {'model': 'custom', 'effort': 'high'}}, {'custom-backup': ['high']}, 'custom'),
        ({'complex': {'model': 'gpt-6.1-sol', 'effort': 'high'}},
         {'gpt-6-sol': {'high': True}, 'gpt-5.6-sol': ['high']}, 'gpt-5.6-sol'),
        ({'complex': {'model': 'gpt-6.1-sol', 'effort': 'high'}},
         {'gpt-6-sol': ('medium', 'high'), 'gpt-5.6-sol': ['high']}, 'gpt-6-sol'),
        ({'complex': {'model': 'gpt-6.1-sol', 'effort': 'high'},
          'normal': {'model': 'gpt-6.1-sol', 'effort': 'medium'}},
         {'gpt-6-sol': ['medium'], 'gpt-5.6-sol': ['high']},
         {'complex': 'gpt-5.6-sol', 'normal': 'gpt-6-sol'})]
    for routes, catalog, models in cases:
        expected = copy.deepcopy(routes)
        if isinstance(models, str):
            for route in expected.values():
                route['model'] = models
        elif models:
            for tier, model in models.items():
                expected[tier]['model'] = model
        before = copy.deepcopy((routes, catalog))
        try:
            result = module.available_routes(routes, catalog)
            checks['compatible_fallback'] &= exact(result, expected)
        except BaseException:
            checks['compatible_fallback'] = False
        checks['no_mutation'] &= (routes, catalog) == before and module.ALTERNATIVES == frozen
    return {key: bool(value) for key, value in checks.items()}


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        data = json.loads(open(sys.argv[1], encoding='utf-8').read())
        print(json.dumps(check(data['sources'], data['alternatives'])))
    except BaseException:
        print(json.dumps({'execution': False}))


if __name__ == '__main__':
    main()
