"""Two reserved repository functions; unchanged external grading and receipts."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests import multifile_trials as base
from tests.coding_trials import decode, sandbox_command

HERE = Path(__file__).resolve().parent
CASE_HASH = 'a365aeabf5ee3b493b9449cbfbc294a490f025b7be5e39b51f8bbafc3ddf7dcc'
GRADER_HASH = 'cb2ab1e1088897c3b7401741e99aeedd808e3e97224b78581003cf618775d96f'
CHECKS = frozenset(('source_contract', 'execution', 'identity_or_provenance', 'boundary_cases', 'no_mutation'))


def manifest():
    data = (HERE/'repository_snapshots/metrics_cases.json').read_bytes()
    worker = (HERE/'metrics_worker.py').read_bytes()
    base.cases()
    if hashlib.sha256(data).hexdigest() != CASE_HASH or hashlib.sha256(worker).hexdigest() != GRADER_HASH:
        raise ValueError('metrics_rubric_changed')
    return json.loads(data)


def grade(case, sources):
    if case not in manifest()['cases']:
        raise ValueError('unknown_case')
    if set(sources) != {'subject.py'} or not base.module_contract(sources['subject.py'], {'subject'}):
        return {'source_contract': False}
    with tempfile.TemporaryDirectory(prefix='metrics-grader-') as tmp:
        root = Path(tmp).resolve()
        (root/'worker.py').write_bytes((HERE/'metrics_worker.py').read_bytes())
        (root/'multifile_worker.py').write_bytes((HERE/'multifile_worker.py').read_bytes())
        (root/'sources.json').write_text(json.dumps({'subject': sources['subject.py']}))
        try:
            value = subprocess.run(sandbox_command(root, str(root/'worker.py'), case['id'], str(root/'sources.json')),
                                   cwd=root, env={'PATH': '/usr/bin:/bin'}, capture_output=True, timeout=4)
            checks = decode(value.stdout) if value.returncode == 0 else {}
            if set(checks) != CHECKS-{'source_contract', 'execution'} or any(type(v) is not bool for v in checks.values()):
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
