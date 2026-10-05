"""Frozen three-task/three-model native coding evaluation, max nine turns.

Default validates graders offline. --live explicitly uses subscription quota.
One attempt per arm, independent ephemeral process, rotated order, no retries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests import coding_trials as grading
from tests.probe_inference_identity import run, PROBE_MODELS


def run_trials(output,max_turns):
    rows=grading.cases();controls=grading.sandbox_controls()
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'schema':'isolated-coding-trials/1','case_sha256':grading.CASE_HASH,'grader_sha256':grading.GRADER_HASH,
        'validator_sha256':hashlib.sha256(Path(grading.__file__).read_bytes()).hexdigest(),
        'scope':'repository_inspired_pure_python_and_review_not_agentic_engineering_benchmark',
        'live':True,'sandbox_controls':controls,'max_turns':max_turns,'attempts':[],
        'policy_activation_eligible':False,'complete_inference_cost_coverage':'unknown'}
    try:
        for n,case in enumerate(rows):
            order=PROBE_MODELS[n:]+PROBE_MODELS[:n]
            for model in order:
                if len(report['attempts'])>=max_turns:break
                sample=run(live=True,model=model,effort='high',exercise=case,
                           checker=lambda text,case_id=case['id']:grading.check_answer(case_id,text))
                # Keep failures and all usage; never silently retry or drop arms.
                sample.update(case_id=case['id'],attempt=1,kind=case['kind'])
                report['attempts'].append(sample)
                with (output/'report.json').open('w',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
                print(json.dumps({'case':case['id'],'model':model,'passed':sample.get('output_check',False),
                                  'failure':sample.get('failure')}),flush=True)
        report['complete_design']=len(report['attempts'])==len(rows)*len(PROBE_MODELS)
        report['passed']=sum(bool(a.get('output_check')) for a in report['attempts'])
    finally:
        with (output/'report.json').open('w',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live',action='store_true');p.add_argument('--output',type=Path)
    p.add_argument('--max-turns',type=int,default=9)
    args=p.parse_args()
    if not 1<=args.max_turns<=9:p.error('max-turns must be 1..9')
    if args.live:
        if not args.output or args.output.exists():p.error('live requires a new output directory')
        report=run_trials(args.output,args.max_turns)
        print(json.dumps({'attempts':len(report['attempts']),'passed':report.get('passed'),
                          'complete_design':report.get('complete_design'),'policy_activation_eligible':False}))
        return int(not report.get('complete_design') or report.get('passed')!=len(report['attempts']))
    print(json.dumps({'live':False,'cases':[c['id'] for c in grading.cases()],
        'sandbox_controls':grading.sandbox_controls(),'case_sha256':grading.CASE_HASH,
        'grader_sha256':grading.GRADER_HASH,'policy_activation_eligible':False}))
    return 0


if __name__=='__main__':sys.exit(main())
