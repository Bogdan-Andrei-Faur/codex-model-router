"""Six isolated native tool-enabled turns maximum; no runtime activation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import queue
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from desktop_runtime import discover
import inference_telemetry as otel
from platform_support import with_loopback_telemetry
from state_store import atomic_json
from tests.smoke_native import Client
from tests.probe_inference_identity import IdentityShapes, PROBE_MODELS
from tests.native_probe_profile import isolated_overrides
from tests import native_probe_profile
from tests import multifile_trials as grading
from tests.coding_trials import sandbox_controls

TOKEN_FIELDS=('inputTokens','cachedInputTokens','outputTokens','reasoningOutputTokens','totalTokens','cacheWriteInputTokens')


class RawEvidence:
    """Retain only safe metadata; never response items, IDs or arbitrary values."""
    def __init__(self):
        self.thread=None;self.turn=None;self.seen=set();self.counts=Counter()
        self.methods=Counter();self.shapes=Counter();self.models=Counter();self.totals=Counter()
        self.missing_usage=0;self.model_linked=0

    def consume(self,message):
        method=message.get('method');params=message.get('params') or {}
        # Native legacy events use params.msg; no raw items are traversed.
        payload=params.get('msg') if isinstance(params.get('msg'),dict) else params
        event_type=payload.get('type')
        if method not in ('rawResponse/completed','codex/event/raw_response_completed') and event_type!='raw_response_completed':return
        self.methods[method if method in ('rawResponse/completed','codex/event/raw_response_completed') else 'other_method']+=1
        # Schema-defined camelCase only. Legacy snake_case fields require an
        # explicitly reviewed adapter, not a guess based on matching values.
        for key in ('responseId','threadId','turnId','usage','usageMetadata'):
            value=payload.get(key);self.shapes[(key,type(value).__name__)]+=1
        if not (self.thread and self.turn and payload.get('threadId')==self.thread and payload.get('turnId')==self.turn):
            self.counts['unjoined']+=1;return
        response=payload.get('responseId')
        if not isinstance(response,str) or not response:self.counts['missing_response_id']+=1;return
        if response in self.seen:self.counts['duplicates']+=1;return
        self.seen.add(response);self.counts['joined']+=1
        usage=payload.get('usage')
        if (isinstance(usage,dict) and all(type(usage.get(k)) is int and 0<=usage[k]<=1_000_000_000 for k in TOKEN_FIELDS[:-1])
                and usage['cachedInputTokens']<=usage['inputTokens'] and usage['reasoningOutputTokens']<=usage['outputTokens']
                and usage['totalTokens']==usage['inputTokens']+usage['outputTokens']):
            for k in TOKEN_FIELDS:
                if type(usage.get(k)) is int and 0<=usage[k]<=1_000_000_000:self.totals[k]+=usage[k]
        else:self.missing_usage+=1
        metadata=payload.get('usageMetadata')
        if isinstance(metadata,dict):
            # Amount units and arbitrary provider metadata have no established
            # identity/currency semantics. Only their structural types survive.
            for k in ('amount','metadata'):self.shapes[('usageMetadata.'+k,type(metadata.get(k)).__name__)]+=1
            body=metadata.get('metadata')
            if isinstance(body,dict):
                known={'model','model_slug','model_name','service_tier','reasoning_effort','cost','credits','currency',
                    'input_tokens','output_tokens','cached_input_tokens','usage','rate_limit','rate_limit_usage'}
                for k,v in body.items():
                    self.shapes[('usageMetadata.metadata.'+(k if k in known else 'other_key'),type(v).__name__)]+=1

    def report(self):
        return {'methods':dict(self.methods),'counts':dict(self.counts),
            'field_types':[{'key':k[0],'type':k[1],'count':v} for k,v in sorted(self.shapes.items())],
            'response_tokens_sum':dict(self.totals) or None,'responses_missing_usage':self.missing_usage,
            'model_linked_responses':self.model_linked,
            'complete_inference_cost_coverage':'unknown','raw_payloads_saved':False,'identity_values_saved':False}


class TrialClient(Client):
    def __init__(self,command,workspace,shapes,raw):
        self.workspace=workspace;self.shapes=shapes;self.raw=raw;self.denied_requests=0
        self.turn_finished=False
        self.items=Counter()
        super().__init__(command)

    def next(self,timeout=45):
        message=self.messages.get(timeout=timeout)
        if message is None:raise RuntimeError('owned_native_closed')
        params=message.get('params') or {};method=message.get('method')
        if method=='item/started':
            kind=(params.get('item') or {}).get('type')
            self.items[kind if kind in ('dynamicToolCall','agentMessage','reasoning','commandExecution','mcpToolCall','webSearch','toolSearch') else 'other_item']+=1
        if method=='turn/started' and params.get('threadId')==self.shapes.native_thread:
            turn=(params.get('turn') or {}).get('id')
            if not self.shapes.native_turn:self.shapes.native_turn=turn;self.raw.turn=turn
        if method=='thread/tokenUsage/updated':self.shapes.consume_usage(params)
        self.raw.consume(message)
        if 'id' in message and method:
            if (method=='item/tool/call' and not self.turn_finished and params.get('threadId')==self.shapes.native_thread
                    and self.shapes.native_turn and params.get('turnId')==self.shapes.native_turn
                    and params.get('namespace')=='trial'):
                success,value=self.workspace.handle(params.get('tool'),params.get('arguments'))
                self.send({'id':message['id'],'result':{'success':success,
                    'contentItems':[{'type':'inputText','text':json.dumps(value)}]}})
            else:
                self.denied_requests+=1
                self.send({'id':message['id'],'error':{'code':-32601,'message':'Outside isolated trial scope'}})
        return message


def run_arm(case,model,effort='high',workspace=None,dynamic_specs=None,task_kind='repair'):
    if model not in PROBE_MODELS or effort not in ('low','medium','high','xhigh'):raise ValueError('isolated_route_unsupported')
    if task_kind not in ('repair','review'):raise ValueError('isolated_task_unsupported')
    shapes=IdentityShapes();raw=RawEvidence();workspace=workspace or grading.Workspace(case)
    collector=otel.LocalInferenceTelemetry(shapes.consume);client=None
    report={'case_id':case['id'],'requested_model':model,'requested_effort':effort,'inference_requests':0,
        'status':'started','evidence_scope':'isolated_experiment_not_desktop_confirmation','policy_activation_eligible':False}
    try:
        install=discover();report['desktop_version']=install.version
        overrides=isolated_overrides();report['native_tool_profile']='code_mode_enabled_scoped_dynamic_tools'
        args=[]
        for key,value in overrides.items():args+=['-c',key+'='+json.dumps(value)]
        args+=['app-server','--analytics-default-enabled']
        client=TrialClient([str(install.backend),*with_loopback_telemetry(args,collector.endpoint,collector.token)],workspace,shapes,raw)
        client.call('initialize',{'clientInfo':{'name':'isolated_multifile_trial','version':'1'},'capabilities':{'experimentalApi':True}})
        client.send({'method':'initialized','params':{}})
        catalog=client.call('model/list',{})['data']
        report['native_catalog']={m['model']:[e['reasoningEffort'] for e in m.get('supportedReasoningEfforts',[])
            if e.get('reasoningEffort') in ('low','medium','high','xhigh')] for m in catalog
            if m['model'] in PROBE_MODELS and not m.get('hidden')}
        if not any(m['model']==model and not m.get('hidden') and any(e['reasoningEffort']==effort for e in m.get('supportedReasoningEfforts',[])) for m in catalog):
            raise ValueError('native_route_unavailable')
        created=client.call('thread/start',{'ephemeral':True,'cwd':str(workspace.root),'model':model,
            'modelProvider':'openai','sandbox':'read-only','approvalPolicy':'never',
            'experimentalRawEvents':True,'dynamicTools':dynamic_specs if dynamic_specs is not None else grading.tools(),
            'baseInstructions':'You are an assistant in a synthetic, isolated coding trial. Use only the provided trial namespace tools to '+
                ('read the fixture files and submit review counterexamples; do not edit files' if task_kind=='review' else 'inspect and repair the fixture files')+
                '. The immutable external grader determines success. Do not access other files or tools.',
            'developerInstructions':'This is an isolated fixture, not work in a user project. Use the provided trial tools through Code Mode (functions.exec), using the exact callable names in its generated tool documentation. Call only tools actually registered for this fixture. No shell, other files, other tools or external data.'})
        shapes.native_thread=created['thread']['id'];raw.thread=shapes.native_thread
        started=time.monotonic();report['inference_requests']=1
        response=client.call('turn/start',{'threadId':shapes.native_thread,'model':model,'effort':effort,
            'input':[{'type':'text','text':case['request']}]})
        shapes.native_turn=response['turn']['id'];raw.turn=shapes.native_turn
        buffered,client.notifications=client.notifications,[];deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            event=buffered.pop(0) if buffered else client.next(max(.1,deadline-time.monotonic()))
            if event.get('method')=='turn/completed' and (event.get('params') or {}).get('turn',{}).get('id')==shapes.native_turn:
                status=event['params']['turn']['status'];report['terminal']=status if status in ('completed','failed','interrupted') else 'other'
                client.turn_finished=True
                break
        else:raise TimeoutError('native_turn_deadline')
        report['turn_elapsed_ms']=round((time.monotonic()-started)*1000)
        drain=time.monotonic()+7
        while time.monotonic()<drain:
            try:client.next(min(.2,max(.01,drain-time.monotonic())))
            except queue.Empty:pass
    except KeyboardInterrupt:
        report.update(failure='owned_harness_interrupted',interrupted=True)
        if client and shapes.native_turn:
            try:client.send({'id':-1,'method':'turn/interrupt','params':{'threadId':shapes.native_thread,'turnId':shapes.native_turn}})
            except Exception:pass
    except Exception as error:report['failure']=type(error).__name__
    finally:
        try:
            if client:client.close();client.temp.cleanup()
        except Exception as error:report['cleanup_failure']=type(error).__name__
        collector.close()
        report.update(workspace.report());workspace.close()
    report.update(shapes.report());report['native_raw_evidence']=raw.report();report['collector']=collector.snapshot()
    report['raw_usage_matches_native_total']=(all(raw.totals.get(k)==v for k,v in (shapes.usage or {}).items())
        if shapes.usage and raw.counts.get('joined') and not raw.missing_usage else None)
    report['denied_native_requests']=client.denied_requests if client else 0
    report['native_item_counts']=dict(client.items) if client else {}
    report['quality_admissible']=bool(client and client.items.get('dynamicToolCall') and workspace.calls)
    report['output_check']=(report.get('terminal')=='completed' and all(report['checks'].values())
        and report['workflow_complete']
        and not report.get('failure') and not report.get('cleanup_failure') and not report['denied_native_requests'])
    report['status']='interrupted' if report.get('interrupted') else 'finished'
    return report


def run_trials(output,max_turns=6,prior_report=None,case_id=None):
    if not 1<=max_turns<=6:raise ValueError('six_turn_bound')
    prior=json.loads(prior_report.read_text()) if prior_report else None
    if prior and (prior.get('schema')!='isolated-multifile-trials/1' or prior.get('case_sha256')!=grading.CASE_HASH
                  or prior.get('grader_sha256')!=grading.GRADER_HASH):raise ValueError('prior_rubric_mismatch')
    previous=prior['attempts'] if prior else []
    # Missing/unfinished request counters count conservatively as one. Native
    # preparation rejected before turn/start consumes no inference turn budget.
    previous_turns=sum(a['inference_requests'] if type(a.get('inference_requests')) is int
        and a['inference_requests'] in (0,1) else 1 for a in previous)
    if previous_turns+max_turns>6:raise ValueError('six_total_turn_bound')
    rows=grading.cases();controls=sandbox_controls();output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'schema':'isolated-multifile-trials/1','case_sha256':grading.CASE_HASH,'grader_sha256':grading.GRADER_HASH,
        'validator_sha256':hashlib.sha256(Path(grading.__file__).read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'native_profile_sha256':hashlib.sha256(Path(native_probe_profile.__file__).read_bytes()).hexdigest(),
        'scope':'two_scoped_multifile_repairs_not_general_engineering_benchmark','sandbox_controls':controls,
        'max_turns':max_turns,'attempts':[dict(a,quality_admissible=False,
            harness_protocol=a.get('harness_protocol','initial_flat_default')) for a in previous],
        'complete_design':False,'policy_activation_eligible':False,
        'complete_inference_cost_coverage':'unknown'}
    current=[]
    for n,case in enumerate(rows):
        if case_id and case['id']!=case_id:continue
        for model in PROBE_MODELS[n:]+PROBE_MODELS[:n]:
            if len(current)>=max_turns or any(a.get('interrupted') for a in current):break
            # Durable intent precedes each native request; interrupted attempts
            # survive instead of disappearing from the cohort/cost denominator.
            intent={'case_id':case['id'],'requested_model':model,'requested_effort':'high','status':'intent',
                'attempt':1+sum(a.get('case_id')==case['id'] and a.get('requested_model')==model for a in previous),
                'harness_protocol':'code_mode_scoped_namespace'}
            current.append(intent);report['attempts'].append(intent);atomic_json(output/'report.json',report)
            try:sample=run_arm(case,model)
            except Exception as error:sample=dict(intent,status='failed',failure=type(error).__name__,output_check=False)
            intent.update(sample);atomic_json(output/'report.json',report)
            print(json.dumps({'case':case['id'],'model':model,'passed':intent.get('output_check',False),
                'failure':intent.get('failure'),'raw_joined':(intent.get('native_raw_evidence') or {}).get('counts',{}).get('joined',0)}),flush=True)
    expected=3 if case_id else 6
    report['completed_primary_design']=len(current)==expected and all(a['status']=='finished' and a.get('quality_admissible') for a in current)
    report['complete_design']=not case_id and report['completed_primary_design']
    report['primary_case']=case_id;report['prior_attempts']=len(previous)
    report['native_turn_requests']=previous_turns+sum(a['inference_requests'] if type(a.get('inference_requests')) is int
        and a['inference_requests'] in (0,1) else 1 for a in current)
    report['passed']=sum(bool(a.get('output_check')) for a in report['attempts']);atomic_json(output/'report.json',report)
    admissible=[a for a in current if a.get('quality_admissible')]
    report['quality_attempts']=len(admissible)
    report['quality_pass_rate']=sum(bool(a.get('output_check')) for a in admissible)/len(admissible) if admissible else None
    report['tool_availability_verified']=bool(admissible)
    atomic_json(output/'report.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--live',action='store_true')
    p.add_argument('--output',type=Path);p.add_argument('--max-turns',type=int,default=6)
    p.add_argument('--prior-report',type=Path);p.add_argument('--case',choices=[c['id'] for c in grading.cases()]);a=p.parse_args()
    if a.live:
        if not a.output or a.output.exists():p.error('live requires a new output directory')
        r=run_trials(a.output,a.max_turns,a.prior_report,a.case);print(json.dumps({'attempts':len(r['attempts']),'passed':r['passed'],'complete_design':r['complete_design'],'completed_primary_design':r['completed_primary_design']}))
        return int(not r['completed_primary_design'])
    print(json.dumps({'cases':[c['id'] for c in grading.cases()],'sandbox_controls':sandbox_controls(),'live':False}))
    return 0


if __name__=='__main__':sys.exit(main())
