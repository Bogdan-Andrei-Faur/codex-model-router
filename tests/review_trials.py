"""Blind scoped review: persist scores only, never submitted findings."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from tests import multifile_trials as base
from tests.coding_trials import require_memory_result, sandbox_command, decode

HERE=Path(__file__).resolve().parent
CASE_HASH='aa84339814dc1cd365b488357633cf9fc40b275e63a329038f9472857a403c78'
GRADER_HASH='bf94cbe6262dece304202ff5adad79b5371024c045546c1c90cac0f71dbf6191'
CHECKS={'submission_contract','all_defects_found','no_false_positives','valid_counterexamples','oracle_consistent','execution'}
COUNTERS={'reported_findings','known_defects','verified_defects','missed_defects','false_positives','invalid_witnesses','duplicate_findings','unexpected_counterexamples'}


def cases():
    manifest=(HERE/'review_cases.json').read_bytes();worker=(HERE/'review_worker.py').read_bytes()
    base.cases()
    if hashlib.sha256(manifest).hexdigest()!=CASE_HASH or hashlib.sha256(worker).hexdigest()!=GRADER_HASH:
        raise ValueError('review_rubric_changed')
    return json.loads(manifest)['cases']


def grade(case,findings):
    if case not in cases():raise ValueError('unknown_review_case')
    modules={Path(p).stem:s for p,s in case['files'].items()}
    if not all(base.module_contract(s,set(modules)) for s in modules.values()):raise ValueError('frozen_source_contract_failed')
    with tempfile.TemporaryDirectory(prefix='review-grader-') as tmp:
        root=Path(tmp).resolve();worker=root/'worker.py';data=root/'review.json'
        worker.write_bytes((HERE/'review_worker.py').read_bytes())
        (root/'multifile_worker.py').write_bytes((HERE/'multifile_worker.py').read_bytes())
        data.write_text(json.dumps({'sources':modules,'findings':findings},allow_nan=False),encoding='utf-8')
        try:
            result=subprocess.run(sandbox_command(root,str(worker),case['id'],str(data)),cwd=root,
                env={'PATH':'/usr/bin:/bin'},capture_output=True,timeout=4)
            require_memory_result(result)
            value=decode(result.stdout) if result.returncode==0 else {}
            checks=value.get('checks') if isinstance(value,dict) else None
            safe={'checks':{k:v for k,v in checks.items() if k in CHECKS and type(v) is bool}} if isinstance(checks,dict) else {}
            if not safe.get('checks'):return {'checks':{'execution':False}}
            for k in COUNTERS:
                if type(value.get(k)) is int and 0<=value[k]<=6:safe[k]=value[k]
            return safe
        except (subprocess.TimeoutExpired,ValueError,UnicodeError):return {'checks':{'execution':False}}


class Workspace:
    def __init__(self,case):
        self.case=case;self.temp=tempfile.TemporaryDirectory(prefix='review-workspace-')
        self.root=Path(self.temp.name).resolve();self.calls=Counter();self.read=set()
        self.rejected=0;self.findings=None
        for p,s in case['files'].items():(self.root/p).write_text(s,encoding='utf-8')

    def handle(self,tool,args):
        self.calls[tool if tool in ('trial_read','trial_submit_findings') else 'other_tool']+=1
        try:
            if sum(self.calls.values())>20 or not isinstance(args,dict):raise ValueError()
            if tool=='trial_read':
                if set(args)!={'path'} or args['path'] not in self.case['files']:raise ValueError()
                p=self.root/args['path']
                if p.is_symlink() or not p.is_file():raise ValueError()
                self.read.add(args['path']);return True,{'source':p.read_text(encoding='utf-8')}
            if tool!='trial_submit_findings' or self.findings is not None or set(args)!={'findings'}:raise ValueError()
            findings=args['findings']
            if not isinstance(findings,list) or len(findings)>6 or len(json.dumps(findings,allow_nan=False).encode())>8192:raise ValueError()
            if not all(isinstance(f,dict) and set(f)=={'function','args'} and f.get('function') in tuple('ABCDEF')
                and isinstance(f.get('args'),dict) for f in findings):raise ValueError()
            self.findings=json.loads(json.dumps(findings,allow_nan=False))
            # Never reveal correctness, expected functions or witness validity.
            return True,{'received':True}
        except (ValueError,TypeError,KeyError,OSError,RecursionError):
            self.rejected+=1;return False,{'rejected':True}

    def report(self):
        intact=all((self.root/p).is_file() and not (self.root/p).is_symlink()
            and (self.root/p).read_text(encoding='utf-8')==s for p,s in self.case['files'].items())
        score=grade(self.case,self.findings) if intact else {'checks':{'fixture_integrity':False}}
        return {'checks':score['checks'],'review_score':{k:v for k,v in score.items() if k in COUNTERS},
            'fixture_unchanged':intact,'harness_invalid':not intact or score['checks'].get('execution') is False or score['checks'].get('oracle_consistent') is False,
            'all_files_read':self.read==set(self.case['files']),'review_submitted':self.findings is not None,
            'workflow_complete':self.read==set(self.case['files']) and self.findings is not None,
            'tool_calls':dict(self.calls),'rejected_tool_calls':self.rejected,'finding_payloads_saved':False}

    def close(self):
        self.findings=None;self.temp.cleanup()


def tools(case):
    read={'type':'function','name':'trial_read','deferLoading':False,'description':'Read one allowed review fixture module.',
        'inputSchema':{'type':'object','properties':{'path':{'type':'string','enum':list(case['files'])}},'required':['path'],'additionalProperties':False}}
    submit={'type':'function','name':'trial_submit_findings','deferLoading':False,
        'description':'Submit once: defective function IDs with concrete counterexample keyword arguments. Returns receipt only, never grader feedback.',
        'inputSchema':{'type':'object','properties':{'findings':{'type':'array','maxItems':6,'items':{
            'type':'object','properties':{'function':{'type':'string','enum':list('ABCDEF')},
                'args':{'type':'object','additionalProperties':True}},'required':['function','args'],'additionalProperties':False}}},
            'required':['findings'],'additionalProperties':False}}
    return [{'type':'namespace','name':'trial','description':'Read-only blind correctness review tools.','tools':[read,submit]}]
