"""Isolated coding exercises; experimental evidence, never policy activation.

Model-generated source exists only in disposable grader directories. Reports
contain checks and safe native metadata, never prompts, code, errors or outputs.
Live source execution requires a verified restrictive macOS Seatbelt profile.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
CASE_HASH='4ec462a97e2d62c3b5cd03fad8e9c754479538becaee1e7b87b47b869d08e062'
GRADER_HASH='5f8e7f3665ef5cb885db6f8c7837d819c1a17b0b6fe7533995da70f558669448'
REVIEW_CODES=frozenset(('CONFIRM_FROM_SETTINGS','FILTER_EXPECTED_MODEL','SUM_CUMULATIVE','DROP_FAILED_ATTEMPTS'))


def cases():
    data=(HERE/'coding_trial_cases.json').read_bytes()
    worker=(HERE/'coding_grader_worker.py').read_bytes()
    if hashlib.sha256(data).hexdigest()!=CASE_HASH or hashlib.sha256(worker).hexdigest()!=GRADER_HASH:
        raise ValueError('coding_rubric_changed')
    return json.loads(data)['cases']


def decode(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate_json_key')
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=unique)


def source_contract(source):
    if not isinstance(source,str) or len(source.encode('utf-8'))>32768:return False
    try:tree=ast.parse(source)
    except (SyntaxError,ValueError,RecursionError):return False
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module]
            if names!=['math'] or getattr(node,'level',0):return False
        elif not isinstance(node,ast.FunctionDef) or node.decorator_list:return False
    forbidden_names={'open','eval','exec','compile','getattr','setattr','delattr','globals','locals','vars','dir','input','print','breakpoint'}
    for node in ast.walk(tree):
        if isinstance(node,(ast.ClassDef,ast.Global,ast.Nonlocal,ast.AsyncFunctionDef)):return False
        if isinstance(node,ast.Name) and (node.id.startswith('__') or node.id in forbidden_names):return False
        if isinstance(node,ast.Attribute) and node.attr.startswith('_'):return False
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('__'):return False
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            if isinstance(node,ast.Import) and any(a.name!='math' for a in node.names):return False
            if isinstance(node,ast.ImportFrom) and (node.module!='math' or node.level):return False
    return True


class SandboxUnavailable(RuntimeError):pass


def require_memory_result(result):
    if result.returncode == 78:
        raise SandboxUnavailable('hard_grader_memory_budget_unavailable')


def profile(root):
    if sys.platform!='darwin' or not shutil.which('sandbox-exec'):
        raise SandboxUnavailable('verified_macos_grader_required')
    roots=['/System','/usr','/Library',str(Path(sys.base_prefix).resolve()),str(root.resolve())]
    ancestors=sorted({str(p) for r in roots for p in Path(r).parents})
    reads=''.join('(subpath '+json.dumps(r)+')' for r in roots)
    reads+=''.join('(literal '+json.dumps(p)+')' for p in ancestors)
    reads+='(literal "/dev/null")(literal "/dev/urandom")'
    executables=[os.path.realpath(sys.executable)]
    framework=Path(sys.base_prefix)/'Resources/Python.app/Contents/MacOS/Python'
    if framework.is_file():executables.append(str(framework.resolve()))
    executable_rules=''.join('(literal '+json.dumps(p)+')' for p in executables)
    return ('(version 1)(deny default)(allow process-exec '+executable_rules+')(allow process-fork)'
            '(allow process-info* (target same-sandbox))(allow sysctl-read)(allow mach-lookup)(allow file-read* '+reads+')')


def sandbox_command(root,*args):
    sandbox_profile = profile(root)
    guard = Path(root) / 'grader_limits.py'
    guard.write_bytes((HERE / 'grader_limits.py').read_bytes())
    return ['/usr/bin/sandbox-exec','-p',sandbox_profile,os.path.realpath(sys.executable),'-I','-S','-B',str(guard),*args]


def sandbox_controls():
    # Synthetic sentinel outside the read grant; no personal files are accessed.
    with tempfile.TemporaryDirectory(prefix='coding-controls-') as tmp:
        root=Path(tmp).resolve();inside=root/'allowed';inside.mkdir()
        secret=root/'sentinel';secret.write_text('synthetic-private-value')
        code="import json,socket\nchecks={}\n"
        code+="for key,call in [(\"read_blocked\",lambda:open("+repr(str(secret))+")),(\"write_blocked\",lambda:open("+repr(str(inside/'write'))+",'w')),(\"network_blocked\",lambda:socket.socket().bind(('127.0.0.1',0)))]:\n"
        code+=" try:call();checks[key]=False\n except OSError:checks[key]=True\nprint(json.dumps(checks))\n"
        control = inside / 'controls.py'
        control.write_text(code, encoding='utf-8')
        result=subprocess.run(sandbox_command(inside,str(control)),env={'PATH':'/usr/bin:/bin'},cwd=inside,
                              capture_output=True,timeout=5)
        require_memory_result(result)
        try:checks=json.loads(result.stdout) if result.returncode==0 else {}
        except ValueError:checks={}
        if checks!={'read_blocked':True,'write_blocked':True,'network_blocked':True}:
            raise SandboxUnavailable('grader_controls_failed')
        return checks


def grade_source(case_id,source):
    if not source_contract(source):return {'source_contract':False}
    with tempfile.TemporaryDirectory(prefix='coding-grader-') as tmp:
        root=Path(tmp).resolve();worker=root/'worker.py';candidate=root/'candidate.py'
        worker.write_bytes((HERE/'coding_grader_worker.py').read_bytes())
        candidate.write_text(source,encoding='utf-8')
        try:
            result=subprocess.run(sandbox_command(root,str(worker),case_id,str(candidate)),
                cwd=root,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=4)
            require_memory_result(result)
            response=decode(result.stdout) if result.returncode==0 else None
            if not isinstance(response,dict) or not isinstance(response.get('checks'),dict):
                return {'source_contract':True,'execution':False}
            # Only fixed grader keys and booleans may leave the child.
            known={'edge_cases','nested_conflict','probability_not_confidence','no_mutation',
                   'supported_routes','astra_boundary','review_boundary','execution'}
            checks={k:v for k,v in response['checks'].items() if k in known and type(v) is bool}
            return dict(source_contract=True,**(checks or {'execution':False}))
        except (subprocess.TimeoutExpired,ValueError,UnicodeError):
            return {'source_contract':True,'execution':False}


def check_answer(case_id,text):
    try:value=decode(text)
    except (ValueError,TypeError,RecursionError):return {'json_contract':False}
    if not isinstance(value,dict):return {'json_contract':False}
    if case_id=='telemetry-review':
        findings=value.get('findings')
        if set(value)!={'findings'} or not isinstance(findings,list) or not all(isinstance(v,str) for v in findings):
            return {'json_contract':False}
        return {'json_contract':True,'all_defects_found':REVIEW_CODES<=set(findings),
                'no_false_positives':set(findings)<=REVIEW_CODES,'no_duplicate_findings':len(findings)==len(set(findings))}
    if set(value)!={'source'}:return {'json_contract':False}
    return dict(json_contract=True,**grade_source(case_id,value['source']))
