"""One opt-in ephemeral echo turn. Safe metadata, no source execution or JEV."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "src"))
from tests.run_multifile_trials import run_arm
from tests import native_probe_profile, run_multifile_trials
from codex_model_router.storage.state_store import atomic_json

CASE={'id':'dynamic-echo-roundtrip','request':
    'Synthetic tool-availability check. You must call trial_echo in the trial namespace with value 37 using the provided Code Mode executor and the exact callable name shown in its generated tool documentation. Then finish briefly. Do not read/write files or call other tools.'}


class EchoWorkspace:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dynamic-echo-');self.root=Path(self.temp.name).resolve()
        self.calls=Counter();self.valid_calls=0;self.rejected=0

    def handle(self,tool,args):
        self.calls[tool if tool=='trial_echo' else 'other_tool']+=1
        if (sum(self.calls.values())<=3 and tool=='trial_echo' and isinstance(args,dict)
                and set(args)=={'value'} and type(args['value']) is int and args['value']==37):
            self.valid_calls+=1;return True,{'value':37}
        self.rejected+=1;return False,{'rejected':True}

    def report(self):
        return {'checks':{'echo_roundtrip':self.valid_calls>0},'workflow_complete':self.valid_calls>0,
            'tool_calls':dict(self.calls),'rejected_tool_calls':self.rejected}

    def close(self):self.temp.cleanup()


def specs():
    return [{'type':'namespace','name':'trial','description':'One synthetic echo tool, no files or external data.',
        'tools':[{'type':'function','name':'trial_echo','description':'Return the fixture value unchanged.',
            'deferLoading':False,'inputSchema':{'type':'object','properties':{'value':{'type':'integer'}},
                'required':['value'],'additionalProperties':False}}]}]


def probe(output):
    output.mkdir(parents=True,mode=0o700,exist_ok=False)
    report={'schema':'isolated-dynamic-echo/1','scope':'native_isolated_roundtrip_not_owner_desktop',
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'max_turns':1,
        'native_runner_sha256':hashlib.sha256(Path(run_multifile_trials.__file__).read_bytes()).hexdigest(),
        'native_profile_sha256':hashlib.sha256(Path(native_probe_profile.__file__).read_bytes()).hexdigest(),
        'attempts':[{'status':'intent','requested_model':'gpt-6-luna','requested_effort':'low'}],
        'policy_activation_eligible':False}
    atomic_json(output/'report.json',report)
    report['attempts'][0].update(run_arm(CASE,'gpt-6-luna',effort='low',workspace=EchoWorkspace(),dynamic_specs=specs()))
    atomic_json(output/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not a.live:print(json.dumps({'live':False,'native_turn_requests':0,'registered_tools':['trial.trial_echo']}));return 0
    if not a.output or a.output.exists():p.error('live requires a new output directory')
    r=probe(a.output);sample=r['attempts'][0]
    print(json.dumps({k:sample.get(k) for k in ('output_check','failure','tool_calls','denied_native_requests','quality_admissible')}))
    return int(not sample.get('output_check'))


if __name__=='__main__':sys.exit(main())
