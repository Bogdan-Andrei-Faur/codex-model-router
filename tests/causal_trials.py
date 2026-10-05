"""Frozen four-module causal-stock repairs; prior corpora remain immutable."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests import multifile_trials as base
from tests.coding_trials import sandbox_command, decode

HERE=Path(__file__).resolve().parent
CASE_HASH='cb3be493bc0f2bceed667e2a8d4baae551b8bd371f2643cbfd822a6ec03c5c8f'
GRADER_HASH='d1df7b822f62aadaaec76076d4cf4573d2cee7986ac9c1a64e7d49ae71c33fc8'
CHECKS=frozenset(('source_contract','execution','canonical_contract','conflict_tombstones','dependency_order',
    'atomic_operations','causal_replay','no_mutation'))


def cases():
    manifest=(HERE/'causal_cases.json').read_bytes();worker=(HERE/'causal_worker.py').read_bytes()
    base.cases()  # Includes the trusted restricted module loader's frozen hash.
    if hashlib.sha256(manifest).hexdigest()!=CASE_HASH or hashlib.sha256(worker).hexdigest()!=GRADER_HASH:
        raise ValueError('causal_rubric_changed')
    return json.loads(manifest)['cases']


def grade(case,sources):
    frozen=cases()
    if case not in frozen:raise ValueError('unknown_causal_case')
    modules={Path(p).stem:s for p,s in sources.items()}
    if set(sources)!=set(case['files']) or not all(base.module_contract(s,set(modules)) for s in modules.values()):
        return {'source_contract':False}
    with tempfile.TemporaryDirectory(prefix='causal-grader-') as tmp:
        root=Path(tmp).resolve();worker=root/'worker.py';candidate=root/'sources.json'
        worker.write_bytes((HERE/'causal_worker.py').read_bytes())
        (root/'multifile_worker.py').write_bytes((HERE/'multifile_worker.py').read_bytes())
        candidate.write_text(json.dumps(modules),encoding='utf-8')
        try:
            result=subprocess.run(sandbox_command(root,str(worker),case['id'],str(candidate)),
                cwd=root,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=4)
            checks=decode(result.stdout) if result.returncode==0 else {}
            safe={k:v for k,v in checks.items() if k in CHECKS and type(v) is bool} if isinstance(checks,dict) else {}
            return dict(source_contract=True,**(safe or {'execution':False}))
        except (subprocess.TimeoutExpired,ValueError,UnicodeError):return {'source_contract':True,'execution':False}


def workspace(case):return base.Workspace(case,grade_fn=grade)


def tools(case):
    specs=base.tools()
    for tool in specs[0]['tools']:
        path=tool['inputSchema']['properties'].get('path')
        if path is not None:path['enum']=list(case['files'])
    return specs
