"""Frozen, scoped multi-module grading. Candidate source is never archived."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests.coding_trials import require_memory_result, source_contract, sandbox_command, decode

HERE=Path(__file__).resolve().parent
CASE_HASH='9ab6c4241f3a91acc9d064e92ad2bdf2f85ed497be5e49cc19039b593fec0ecd'
GRADER_HASH='a1d9724d0a361d116ea800ed9b2c53ff848a6dee49ecaea596d19e3475a575ab'
CHECKS=frozenset(('source_contract','execution','snapshot_contract','all_attempts_and_coverage',
                 'plan_contract','caller_respects_decision','no_mutation'))


def cases():
    data=(HERE/'multifile_cases.json').read_bytes()
    worker=(HERE/'multifile_worker.py').read_bytes()
    if hashlib.sha256(data).hexdigest()!=CASE_HASH or hashlib.sha256(worker).hexdigest()!=GRADER_HASH:
        raise ValueError('multifile_rubric_changed')
    return json.loads(data)['cases']


def module_contract(source,names):
    if not isinstance(source,str) or len(source.encode('utf-8'))>32768:return False
    try:
        tree=ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module]
                if getattr(node,'level',0) or any(n not in names|{'math'} for n in modules):return False
                if any(a.name=='*' or a.name.startswith('_') or a.asname and a.asname.startswith('_') for a in node.names):return False
        # The generic validator checks every other AST restriction; only the
        # reviewed sibling import exception is removed from its temporary AST.
        tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
        return source_contract(ast.unparse(tree))
    except (SyntaxError,ValueError,RecursionError,UnicodeError):return False


def grade(case,sources):
    modules={Path(p).stem:s for p,s in sources.items()}
    if set(sources)!=set(case['files']) or not all(module_contract(s,set(modules)) for s in modules.values()):
        return {'source_contract':False}
    # Check frozen rubric at every boundary, before running generated code.
    cases()
    with tempfile.TemporaryDirectory(prefix='multifile-grader-') as tmp:
        root=Path(tmp).resolve();worker=root/'worker.py';candidate=root/'sources.json'
        worker.write_bytes((HERE/'multifile_worker.py').read_bytes())
        candidate.write_text(json.dumps(modules),encoding='utf-8')
        try:
            result=subprocess.run(sandbox_command(root,str(worker),case['id'],str(candidate)),
                cwd=root,env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=4)
            require_memory_result(result)
            checks=decode(result.stdout) if result.returncode==0 else {}
            safe={k:v for k,v in checks.items() if k in CHECKS and type(v) is bool} if isinstance(checks,dict) else {}
            return dict(source_contract=True,**(safe or {'execution':False}))
        except (subprocess.TimeoutExpired,ValueError,UnicodeError):return {'source_contract':True,'execution':False}


class Workspace:
    """Only owned fixture files, no filesystem tool and no grader exposure."""
    def __init__(self,case,grade_fn=grade):
        self.case=case;self.grade=grade_fn;self.temp=tempfile.TemporaryDirectory(prefix='multifile-workspace-')
        self.root=Path(self.temp.name).resolve();self.read=set();self.written=set()
        self.calls=Counter();self.rejected=0;self.revision=0;self.tested_revision=None
        for name,source in case['files'].items():(self.root/name).write_text(source,encoding='utf-8')

    def sources(self):return {p:(self.root/p).read_text(encoding='utf-8') for p in self.case['files']}

    def handle(self,tool,args):
        self.calls[tool if tool in ('trial_read','trial_write','trial_test') else 'other_tool']+=1
        try:
            if sum(self.calls.values())>40 or not isinstance(args,dict):raise ValueError()
            if tool=='trial_test':
                if args:raise ValueError()
                checks=self.grade(self.case,self.sources());passed=bool(checks) and all(checks.values())
                if passed:self.tested_revision=self.revision
                return True,{'checks':checks,'passed':passed}
            if tool not in ('trial_read','trial_write'):raise ValueError()
            expected={'path'} if tool=='trial_read' else {'path','source'}
            if set(args)!=expected or args['path'] not in self.case['files']:raise ValueError()
            name=args['path'];path=self.root/name
            if path.is_symlink() or not path.is_file():raise ValueError()
            if tool=='trial_read':
                self.read.add(name);return True,{'source':path.read_text(encoding='utf-8')}
            if not module_contract(args['source'],{Path(p).stem for p in self.case['files']}):raise ValueError()
            path.write_text(args['source'],encoding='utf-8');self.written.add(name);self.revision+=1
            return True,{'written':True}
        except (ValueError,TypeError,KeyError,OSError):
            self.rejected+=1;return False,{'rejected':True}

    def report(self):
        checks=self.grade(self.case,self.sources())
        return {'checks':checks,'all_files_read':self.read==set(self.case['files']),
            'all_files_written':self.written==set(self.case['files']),
            'successful_test_on_final_revision':self.tested_revision==self.revision,
            'workflow_complete':self.read==set(self.case['files']) and self.written==set(self.case['files']) and self.tested_revision==self.revision,
            'tool_calls':dict(self.calls),'rejected_tool_calls':self.rejected}

    def close(self):self.temp.cleanup()


def tools():
    result=[]
    for name,properties in (
        ('trial_read',{'path':{'type':'string'}}),
        ('trial_write',{'path':{'type':'string'},'source':{'type':'string'}}),('trial_test',{})):
        result.append({'type':'function','name':name,'deferLoading':False,
            'description':{'trial_read':'Read one allowed fixture module.',
                'trial_write':'Replace one allowed fixture module with pure Python source.',
                'trial_test':'Run the immutable external integration checks.'}[name],
            'inputSchema':{'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}})
    return [{'type':'namespace','name':'trial','description':'Scoped synthetic fixture tools only.','tools':result}]
