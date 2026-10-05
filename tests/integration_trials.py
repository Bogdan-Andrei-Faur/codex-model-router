"""New frozen three-module repairs; previous multifile rubric is immutable."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests import multifile_trials as base
from tests.coding_trials import require_memory_result, run_sandbox, decode

HERE=Path(__file__).resolve().parent
CASE_HASH='909ed83f877f452e69791e3a7f9922946e4d8d1f6897e11114c8c8304000cfad'
GRADER_HASH='f5ceec3be693d7c030586308f90d8b7a91cfbf0b9343afc1530c3fe8442c4281'
CHECKS=frozenset(('source_contract','execution','normalization','conflict_dedup','coverage_totals',
    'cancellation_contract','terminal_order','no_mutation'))


def cases():
    manifest=(HERE/'integration_cases.json').read_bytes();worker=(HERE/'integration_worker.py').read_bytes()
    base.cases()  # Includes the trusted restricted module loader's frozen hash.
    if hashlib.sha256(manifest).hexdigest()!=CASE_HASH or hashlib.sha256(worker).hexdigest()!=GRADER_HASH:
        raise ValueError('integration_rubric_changed')
    return json.loads(manifest)['cases']


def grade(case,sources):
    frozen=cases()
    if case not in frozen:raise ValueError('unknown_integration_case')
    modules={Path(p).stem:s for p,s in sources.items()}
    if set(sources)!=set(case['files']) or not all(base.module_contract(s,set(modules)) for s in modules.values()):
        return {'source_contract':False}
    with tempfile.TemporaryDirectory(prefix='integration-grader-') as tmp:
        root=Path(tmp).resolve();worker=root/'worker.py';candidate=root/'sources.json'
        worker.write_bytes((HERE/'integration_worker.py').read_bytes())
        (root/'multifile_worker.py').write_bytes((HERE/'multifile_worker.py').read_bytes())
        candidate.write_text(json.dumps(modules),encoding='utf-8')
        try:
            result=run_sandbox(root,str(worker),case['id'],str(candidate), timeout=4)
            require_memory_result(result)
            checks=decode(result.stdout) if result.returncode==0 else {}
            safe={k:v for k,v in checks.items() if k in CHECKS and type(v) is bool} if isinstance(checks,dict) else {}
            return dict(source_contract=True,**(safe or {'execution':False}))
        except (subprocess.TimeoutExpired,ValueError,UnicodeError):return {'source_contract':True,'execution':False}


def workspace(case):return base.Workspace(case,grade_fn=grade)
