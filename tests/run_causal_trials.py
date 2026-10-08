"""Three native requests for one frozen four-module causal-stock repair."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "src"))
from codex_model_router.storage.state_store import atomic_json
from tests import causal_trials as grading, native_probe_profile, multifile_trials
from tests.coding_trials import sandbox_controls
from tests.probe_inference_identity import PROBE_MODELS
from tests.run_multifile_trials import run_arm
from tests import run_multifile_trials


def design_trials():
    return [{'case_id':case['id'],'requested_model':m,'requested_effort':'high','attempt':1}
        for case in grading.cases() for m in PROBE_MODELS]


def run_trials(output,max_turns=3):
    planned=design_trials()
    if max_turns is None:max_turns=len(planned)
    if type(max_turns) is not int or not 1<=max_turns<=len(planned):raise ValueError('design_turn_bound')
    rows={c['id']:c for c in grading.cases()};controls=sandbox_controls()
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'schema':'isolated-causal-trials/1','case_sha256':grading.CASE_HASH,
        'grader_sha256':grading.GRADER_HASH,'module_loader_sha256':multifile_trials.GRADER_HASH,
        'validator_sha256':hashlib.sha256(Path(grading.__file__).read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'native_runner_sha256':hashlib.sha256(Path(run_multifile_trials.__file__).read_bytes()).hexdigest(),
        'workspace_sha256':hashlib.sha256(Path(multifile_trials.__file__).read_bytes()).hexdigest(),
        'native_profile_sha256':hashlib.sha256(Path(native_probe_profile.__file__).read_bytes()).hexdigest(),
        'scope':'one_frozen_four_module_causal_repair_not_desktop_or_general_engineering',
        'sandbox_controls':controls,'max_turns':max_turns,'attempts':[],
        'design':'three-model-high','planned_turns':planned,
        'design_sha256':hashlib.sha256(json.dumps(planned,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'policy_activation_eligible':False,'complete_inference_cost_coverage':'unknown'}
    stop=False
    for spec in planned:
        if stop or len(report['attempts'])>=max_turns:break
        case=rows[spec['case_id']];model=spec['requested_model'];effort=spec['requested_effort']
        intent=dict(spec,status='intent',harness_protocol='code_mode_scoped_namespace')
        report['attempts'].append(intent);atomic_json(output/'report.json',report)
        owned=None
        try:
            owned=grading.workspace(case)
            intent.update(run_arm(case,model,effort=effort,workspace=owned,dynamic_specs=grading.tools(case)))
        except KeyboardInterrupt:
            intent.update(status='interrupted',interrupted=True,output_check=False);stop=True
        except Exception:
            intent.update(status='failed',failure='owned_harness_failure',output_check=False);stop=True
        finally:
            if owned:
                try:owned.close()
                except Exception:intent['cleanup_failure']='owned_workspace_cleanup_failure';stop=True
        # Quality failure with otherwise complete instrumentation stays in
        # the comparison. Infrastructure/harness problems stop the quota.
        stop=stop or bool(intent.get('failure') or intent.get('cleanup_failure')
            or intent.get('checks',{}).get('execution') is False
            or intent.get('denied_native_requests') or intent.get('interrupted')
            or intent.get('terminal')!='completed' or intent.get('quality_admissible') is not True)
        intent['tool_execution_observed']=intent.get('quality_admissible') is True
        if stop:intent['quality_admissible']=False
        atomic_json(output/'report.json',report)
        print(json.dumps({'case':case['id'],'model':model,'requested_effort':effort,
            'passed':intent.get('output_check') is True,'quality_admissible':intent.get('quality_admissible') is True,
            'campaign_stopped':stop}),flush=True)
    attempts=report['attempts'];admissible=[a for a in attempts if a.get('quality_admissible') is True]
    report.update(native_turn_requests=sum(a['inference_requests'] if type(a.get('inference_requests')) is int
        and a['inference_requests'] in (0,1) else 1 for a in attempts),campaign_stopped=stop,
        complete_design=len(attempts)==len(planned) and not stop,quality_attempts=len(admissible),
        passed=sum(a.get('output_check') is True for a in admissible),
        quality_pass_rate=sum(a.get('output_check') is True for a in admissible)/len(admissible) if admissible else None)
    atomic_json(output/'report.json',report);return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true')
    p.add_argument('--output',type=Path);p.add_argument('--max-turns',type=int)
    a=p.parse_args()
    if not a.live:
        print(json.dumps({'planned_turns':design_trials(),'native_calls':0}));return 0
    if not a.output or a.output.exists():p.error('requires a new output directory')
    report=run_trials(a.output,a.max_turns)
    print(json.dumps({k:report[k] for k in ('native_turn_requests','passed','quality_attempts','complete_design','campaign_stopped')}))
    return 0


if __name__=='__main__':sys.exit(main())
