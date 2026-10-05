"""Frozen repository function extraction plus declared trusted scaffolding."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests import multifile_trials as base
from tests.coding_trials import require_memory_result, decode, run_sandbox

HERE = Path(__file__).resolve().parent
CASE_HASH = '5ae098d4fdf46e659944226be0949c6dfcf8fca22a1f3c8e998baa5c5f832960'
GRADER_HASH = '9e770ac83e569958f8077ebcd0c109918151fafc3e915b5eb4938b540a90fe6a'
CHECKS = frozenset(('source_contract', 'execution', 'compatible_fallback',
                    'priority_and_original', 'no_mutation', 'deep_copy_and_fields'))


def manifest():
    data = (HERE/'repository_snapshots/catalog_cases.json').read_bytes()
    worker = (HERE/'repository_worker.py').read_bytes()
    base.cases()
    if hashlib.sha256(data).hexdigest() != CASE_HASH or hashlib.sha256(worker).hexdigest() != GRADER_HASH:
        raise ValueError('repository_rubric_changed')
    return json.loads(data)


def cases():
    return manifest()['cases']


def grade(case, sources):
    data = manifest()
    if case not in data['cases']:
        raise ValueError('unknown_repository_case')
    if (set(sources) != set(case['files'])
            or not all(base.module_contract(s, {'catalog'}) for s in sources.values())):
        return {'source_contract': False}
    with tempfile.TemporaryDirectory(prefix='repository-grader-') as tmp:
        root = Path(tmp).resolve()
        worker = root/'worker.py'; worker.write_bytes((HERE/'repository_worker.py').read_bytes())
        (root/'multifile_worker.py').write_bytes((HERE/'multifile_worker.py').read_bytes())
        candidate = root/'sources.json'
        candidate.write_text(json.dumps({'sources': {Path(p).stem: s for p, s in sources.items()},
            'alternatives': data['scaffolding']['ALTERNATIVES']}), encoding='utf-8')
        try:
            result = run_sandbox(root, str(worker), str(candidate), timeout=4)
            require_memory_result(result)
            checks = decode(result.stdout) if result.returncode == 0 else {}
            if (not isinstance(checks, dict) or set(checks) != CHECKS-{'source_contract', 'execution'}
                    or not all(type(v) is bool for v in checks.values())):
                return {'source_contract': True, 'execution': False}
            return dict(source_contract=True, **checks)
        except (subprocess.TimeoutExpired, ValueError, UnicodeError):
            return {'source_contract': True, 'execution': False}


def tools(case):
    specs = base.tools()
    for tool in specs[0]['tools']:
        if 'path' in tool['inputSchema']['properties']:
            tool['inputSchema']['properties']['path']['enum'] = list(case['files'])
    return specs
