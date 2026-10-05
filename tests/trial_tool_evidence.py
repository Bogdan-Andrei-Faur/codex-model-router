"""Protocol2 owned workspace: bounded metadata only, unchanged model receipts."""
from collections import Counter
import json
from pathlib import Path

from tests import multifile_trials as base

TOOLS=('trial_read','trial_write','trial_test')
REJECTIONS=frozenset(('call_limit','invalid_arguments','unsupported_tool','path_not_allowed',
                     'unsafe_file','source_contract','filesystem_error'))
GRADER_ERRORS=frozenset(('invalid_result','grader_exception','execution_unavailable'))
MAX_EVENTS=40


class Rejected(Exception):
    def __init__(self,reason):self.reason=reason


class Workspace(base.Workspace):
    def __init__(self,case,grade_fn,check_names):
        self.check_names=frozenset(check_names);self.grade_fn=grade_fn
        self.events=[];self.events_dropped=0;self.rejection_categories=Counter()
        self.grader_error_categories=Counter();self.harness_invalid=False
        super().__init__(case,grade_fn=self.checked_grade)

    def checked_grade(self,case,sources):
        try:
            checks=self.grade_fn(case,sources)
            if not isinstance(checks,dict) or not checks or any(
                k not in self.check_names or type(v) is not bool for k,v in checks.items()):
                self.grader_error_categories['invalid_result']+=1;self.harness_invalid=True
                return {'execution':False}
            complete=(set(checks)==self.check_names-{'execution'} or
                      checks=={'source_contract':False} or
                      checks.get('execution') is False and set(checks)<={'source_contract','execution'})
            if not complete:
                self.grader_error_categories['invalid_result']+=1;self.harness_invalid=True
                return {'execution':False}
            if checks.get('execution') is False:
                self.grader_error_categories['execution_unavailable']+=1;self.harness_invalid=True
            return dict(checks)
        except Exception:
            self.grader_error_categories['grader_exception']+=1;self.harness_invalid=True
            return {'execution':False}

    def append(self,event):
        if len(self.events)<MAX_EVENTS:self.events.append(event)
        else:self.events_dropped+=1

    def handle(self,tool,args):
        name=tool if tool in TOOLS else 'other_tool';self.calls[name]+=1
        event={'sequence':sum(self.calls.values()),'tool':name,'revision_before':self.revision}
        try:
            if sum(self.calls.values())>40:raise Rejected('call_limit')
            if not isinstance(args,dict):raise Rejected('invalid_arguments')
            if tool=='trial_test':
                if args:raise Rejected('invalid_arguments')
                checks=self.grade(self.case,self.sources());passed=bool(checks) and all(checks.values())
                if passed:self.tested_revision=self.revision
                event.update(status='accepted',checks=checks,passed=passed,
                             evaluation_available=checks.get('execution') is not False)
                reply={'checks':checks,'passed':passed}
            else:
                if tool not in ('trial_read','trial_write'):raise Rejected('unsupported_tool')
                expected={'path'} if tool=='trial_read' else {'path','source'}
                if set(args)!=expected or not isinstance(args['path'],str):raise Rejected('invalid_arguments')
                path_name=args['path']
                if path_name not in self.case['files']:raise Rejected('path_not_allowed')
                path=self.root/path_name
                if path.is_symlink() or not path.is_file():raise Rejected('unsafe_file')
                if tool=='trial_read':
                    reply={'source':path.read_text(encoding='utf-8')};self.read.add(path_name)
                else:
                    try:valid=base.module_contract(args['source'],{Path(p).stem for p in self.case['files']})
                    except UnicodeError:valid=False
                    if not valid:
                        raise Rejected('source_contract')
                    path.write_text(args['source'],encoding='utf-8');self.written.add(path_name);self.revision+=1
                    reply={'written':True}
                event['status']='accepted'
            event['revision_after']=self.revision;self.append(event)
            return True,reply
        except Rejected as error:reason=error.reason
        except (OSError,UnicodeError):reason='filesystem_error'
        except (ValueError,TypeError,KeyError,RecursionError):reason='invalid_arguments'
        self.rejected+=1;self.rejection_categories[reason]+=1
        event.update(status='rejected',rejection_category=reason,revision_after=self.revision)
        self.append(event);return False,{'rejected':True}

    def report(self):
        result=super().report()
        result.update(tool_evidence_protocol='scoped-tool-metadata/2',
            tool_events=json.loads(json.dumps(self.events)),tool_events_dropped=self.events_dropped,
            tool_trace_complete=self.events_dropped==0,
            rejection_categories=dict(self.rejection_categories),grader_error_categories=dict(self.grader_error_categories),
            harness_invalid=self.harness_invalid,tool_payloads_saved=False)
        return result
