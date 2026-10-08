"""Maximum6 new native review turns; immutable counterexample checks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / "src"))
from codex_model_router.storage.state_store import atomic_json
from tests import review_trials as grading, native_probe_profile, multifile_trials, run_multifile_trials
from tests.coding_trials import sandbox_controls
from tests.probe_inference_identity import PROBE_MODELS
from tests.run_multifile_trials import run_arm


def design_trials(case_id=None):
    cases=grading.cases()
    if case_id is not None and case_id not in {c['id'] for c in cases}:raise ValueError('unknown_review_case')
    return [{'case_id':case['id'],'requested_model':m,'requested_effort':'high','attempt':1}
        for n,case in enumerate(cases) if case_id is None or case['id']==case_id
        for m in PROBE_MODELS[n:]+PROBE_MODELS[:n]]


def run_trials(output,max_turns=6,case_id=None):
    if type(max_turns) is not int or not 1<=max_turns<=6:raise ValueError('six_turn_bound')
    planned=design_trials(case_id);cases=grading.cases();controls=sandbox_controls()
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'schema':'isolated-review-trials/1','case_sha256':grading.CASE_HASH,'grader_sha256':grading.GRADER_HASH,
        'module_loader_sha256':multifile_trials.GRADER_HASH,'max_turns':max_turns,'case_filter':case_id,'planned_turns':planned,
        'design_sha256':hashlib.sha256(json.dumps(planned,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'native_runner_sha256':hashlib.sha256(Path(run_multifile_trials.__file__).read_bytes()).hexdigest(),
        'validator_sha256':hashlib.sha256(Path(grading.__file__).read_bytes()).hexdigest(),
        'native_profile_sha256':hashlib.sha256(Path(native_probe_profile.__file__).read_bytes()).hexdigest(),
        'sandbox_controls':controls,'attempts':[],'policy_activation_eligible':False,
        'complete_inference_cost_coverage':'unknown','scope':'closed_function_correctness_reviews_not_general_security_or_desktop_validation'}
    stop=False;by_id={c['id']:c for c in cases}
    for spec in planned:
        if stop or len(report['attempts'])>=max_turns:break
        intent=dict(spec,status='intent');report['attempts'].append(intent);atomic_json(output/'report.json',report)
        owned=None
        try:
            owned=grading.Workspace(by_id[spec['case_id']])
            intent.update(run_arm(owned.case,spec['requested_model'],effort='high',workspace=owned,
                dynamic_specs=grading.tools(owned.case),task_kind='review'))
        except KeyboardInterrupt:intent.update(status='interrupted',interrupted=True,output_check=False);stop=True
        except Exception:intent.update(status='failed',failure='owned_review_harness_failure',output_check=False);stop=True
        finally:
            if owned:
                try:owned.close()
                except Exception:intent['cleanup_failure']='owned_review_cleanup_failure';stop=True
        stop=stop or bool(intent.get('failure') or intent.get('cleanup_failure') or intent.get('harness_invalid')
            or intent.get('denied_native_requests') or intent.get('interrupted')
            or intent.get('terminal')!='completed' or intent.get('quality_admissible') is not True)
        intent['tool_execution_observed']=intent.get('quality_admissible') is True
        if stop:intent['quality_admissible']=False
        atomic_json(output/'report.json',report)
        print(json.dumps({'case':spec['case_id'],'model':spec['requested_model'],'passed':intent.get('output_check') is True,
            'review_score':intent.get('review_score'),'campaign_stopped':stop}),flush=True)
    admissible=[a for a in report['attempts'] if a.get('quality_admissible') is True]
    report.update(native_turn_requests=sum(a['inference_requests'] if type(a.get('inference_requests')) is int
        and a['inference_requests'] in (0,1) else 1 for a in report['attempts']),quality_attempts=len(admissible),
        passed=sum(a.get('output_check') is True for a in admissible),complete_design=len(report['attempts'])==6 and not stop,
        complete_selected_design=len(report['attempts'])==len(planned) and not stop,
        campaign_stopped=stop)
    atomic_json(output/'report.json',report);return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true')
    p.add_argument('--output',type=Path);p.add_argument('--max-turns',type=int,default=6)
    p.add_argument('--case',choices=[c['id'] for c in grading.cases()]);a=p.parse_args()
    if not a.live:
        print(json.dumps({'planned_turns':design_trials(a.case),'native_calls':0,'max_live_turns':6}));return 0
    if not a.output or a.output.exists():p.error('requires a new output directory')
    r=run_trials(a.output,a.max_turns,a.case);print(json.dumps({k:r[k] for k in ('native_turn_requests','quality_attempts','passed','complete_design','complete_selected_design','campaign_stopped')}));return 0


if __name__=='__main__':sys.exit(main())
