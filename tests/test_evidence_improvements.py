import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.bridge.router import Router
from codex_model_router.telemetry.inference_attribution import COUNTERS
from codex_model_router.telemetry.evidence import export, scrub, summarize, SCHEMA
from codex_model_router.evaluation.outcome_evaluation import record_check, evaluate_checks
from codex_model_router.storage.state_store import append_record, read_records


class AttributionRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name); config = root/'config.json'; config.write_text('{}')
        self.router = Router(config,root/'state')
        self.router.threads['thread-one'] = {'phase_status':'active','phase_model':'gpt-6.1-sol',
            'phase_effort':'high','phase_id':'phase-one','turn_id':'turn-one',
            'phase_accepted_at':time.time()-2,'decision_started_at':time.time()-3}
        self.router.current_decisions['thread-one'] = 'decision-one'
        self.record = {'model':'gpt-6-luna','effort':'low','thread_id':'thread-one','turn_id':'turn-one',
                       'timestamp':time.time(),'event_id':'event-one','event_kind':'response.completed'}

    def tearDown(self):
        self.temp.cleanup()

    def test_identity_matched_unexpected_model_is_observed_not_discarded(self):
        self.router.observe_inference(self.record)
        row = self.router.threads['thread-one']
        self.assertEqual(row['observed_model'],'gpt-6-luna')
        self.assertEqual(row['phase_model'],'gpt-6.1-sol')
        self.assertTrue(row['inference_model_mismatch'])
        self.assertTrue(row['inference_effort_mismatch'])
        event = list(read_records(self.router.state_dir/'history.jsonl'))[-1]
        self.assertEqual(event['turn_id'],'turn-one')
        self.assertEqual(event['evidence_confidence'],'confirmed')
        self.assertEqual(event['expected_model'],'gpt-6.1-sol')
        self.assertEqual(self.router.stats['telemetry_model_mismatch'],1)

    def test_missing_ids_never_promote_matching_model(self):
        record = {**self.record,'model':'gpt-6.1-sol','effort':'high'}
        record.pop('turn_id')
        self.router.observe_inference(record)
        self.assertNotIn('observed_model',self.router.threads['thread-one'])
        self.assertEqual(self.router.stats['telemetry_missing_turn_id'],1)
        self.assertEqual(list(read_records(self.router.state_dir/'history.jsonl'))[-1]['event'],'inference_probable')

    def test_phase_without_timestamp_is_only_probable(self):
        record = {**self.record,'model':'gpt-6.1-sol','effort':'high'}; record.pop('timestamp')
        self.router.observe_inference(record)
        self.assertEqual(self.router.stats['telemetry_confirmed'],0)
        self.assertEqual(self.router.stats['telemetry_missing_timestamp'],1)

    def test_duplicate_is_counted_and_not_observed_twice(self):
        for _ in range(2): self.router.observe_inference(self.record)
        self.assertEqual(self.router.stats['telemetry_duplicates'],1)
        self.assertEqual(self.router.stats['telemetry_confirmed'],1)

    def test_stale_old_turn_unknown_thread_and_future_are_distinct(self):
        self.router.observe_inference({**self.record,'timestamp':time.time()-10,'event_id':'stale'})
        self.router.observe_inference({**self.record,'turn_id':'other-turn','event_id':'turn'})
        self.router.observe_inference({**self.record,'thread_id':'unknown-thread','event_id':'thread'})
        self.router.observe_inference({**self.record,'timestamp':time.time()+100,'event_id':'future'})
        for reason in ('stale','turn_mismatch','unknown_thread','invalid_timestamp'):
            self.assertEqual(self.router.stats['telemetry_'+reason],1)
        self.assertEqual(self.router.stats['telemetry_confirmed'],0)

    def test_ambiguity_is_not_resolved_by_inventing_ids(self):
        self.router.threads['thread-two'] = dict(self.router.threads['thread-one'],turn_id='turn-two')
        record = {**self.record,'model':'gpt-6.1-sol','effort':'high'}
        record.pop('thread_id');record.pop('turn_id')
        self.router.observe_inference(record)
        self.assertEqual(self.router.stats['telemetry_ambiguous'],1)
        self.assertEqual(self.router.stats['telemetry_missing_thread_id'],1)

    def test_mismatched_request_metrics_never_claim_completion(self):
        self.router.observe_inference({**self.record,'event_kind':'response.failed','event_name':'codex.api_request'})
        self.assertEqual(self.router.stats['telemetry_confirmed'],0)
        row = list(read_records(self.router.state_dir/'history.jsonl'))[-1]
        self.assertEqual(row['event'],'inference_metric')
        self.assertTrue(row['inference_model_mismatch'])
        self.assertNotIn('observed_model',self.router.threads['thread-one'])

    def test_all_monitors_forward_stage_counters(self):
        from codex_model_router.monitor.monitor_state import TELEMETRY_COUNTERS
        root = Path(__file__).resolve().parents[1]
        for counter in COUNTERS:
            self.assertIn(counter,TELEMETRY_COUNTERS)
        for name in ('native/macos/MonitorMac.swift','native/windows/MonitorWindows.cs'):
            self.assertIn('monitor_service.py',(root/name).read_text())


class CommonEvidence(unittest.TestCase):
    def test_export_scrubs_every_private_channel_and_preserves_joins(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state'; state.mkdir()
            raw={'event':'decision_created','decision_id':'PRIVATE_ID','thread':'PRIVATE_THREAD',
                 'product_version':'0.8.1','time':1,'title':'SECRET_TITLE','prompt':'SECRET_PROMPT',
                 'response':'SECRET_OUTPUT','token':'SECRET_TOKEN','account_usage':{'secret':'SECRET_ACCOUNT'},
                 'model':'gpt-6.1-sol'}
            append_record(state,raw); append_record(state,raw)
            append_record(state,{'event':'inference_observed','decision_id':'PRIVATE_ID','observed_model':'gpt-6.1-sol','time':2})
            (state/'status-1.json').write_text(json.dumps({'heartbeat':time.time(),'stats':{'telemetry_duplicates':3,'telemetry_secret':'SECRET_STATS'},'threads':{'private':'SECRET_THREAD'},'telemetry':{'requests':4}}))
            output=Path(folder)/'evidence.zip'; summary=export(state,output,'macos')
            with ZipFile(output) as z:
                body=''.join(z.read(x).decode() for x in z.namelist())
                self.assertNotIn('SECRET_',body);self.assertNotIn('PRIVATE_',body)
                rows=[json.loads(l) for l in z.read('events.jsonl').splitlines()]
                self.assertEqual(rows[0]['decision_id'],rows[1]['decision_id'])
                manifest=json.loads(z.read('manifest.json'))
                self.assertEqual(manifest['schema'],SCHEMA)
                self.assertEqual(manifest['exact_duplicate_records_removed'],1)
            self.assertEqual(summary['legacy_observed_events'],1)
            self.assertEqual(summary['confirmed_inference_events'],0)
            with self.assertRaises(FileExistsError):export(state,output)

    def test_legacy_ubuntu_and_windows_layouts_produce_same_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for label,name in [('ubuntu','root/data/history.jsonl'),('windows','data/history.jsonl')]:
                source=root/(label+'.zip')
                with ZipFile(source,'w') as z:
                    z.writestr(name,json.dumps({'event':'decision_created','decision_id':'d','time':1})+'\n')
                    z.writestr('normalized/events.jsonl','UNTRUSTED_NOT_READ')
                out=root/(label+'-new.zip');result=export(source,out,label)
                self.assertEqual(result['created_decisions'],1)
                self.assertEqual(result['execution_provenance'],{'unknown':1})
                reexport=root/(label+'-again.zip'); again=export(out,reexport,label)
                self.assertEqual(again['created_decisions'],1)

    def test_cumulative_usage_not_summed_and_unconfirmed_estimates_excluded(self):
        rows=[{'event':'decision_created','decision_id':'d'},
              {'event':'decision_usage','decision_id':'d','inputTokens':10},
              {'event':'decision_usage','decision_id':'d','inputTokens':20},
              {'event':'inference_observed','decision_id':'d','estimated_api_standard_usd':99}]
        result=summarize(rows)
        self.assertEqual(result['last_native_usage_totals']['inputTokens'],20)
        self.assertEqual(result['estimated_standard_api_usd'],0)
        self.assertFalse(result['billed_cost_observed'])

    def test_invalid_enums_nan_and_content_do_not_survive_scrubbing(self):
        row=scrub({'event':'native_turn_error','decision_id':'d','will_retry':True,'error_type':'SECRET_ERROR',
                   'model':'SECRET_MODEL','engine_latency_ms':float('nan'),'prompt':'SECRET_PROMPT'},b'key')
        self.assertNotIn('SECRET',json.dumps(row))
        self.assertNotIn('engine_latency_ms',row)
        self.assertTrue(row['will_retry'])

    def test_scope_labels_are_bounded_before_any_output_is_created(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'out.zip'
            with self.assertRaisesRegex(ValueError,'invalid_export_scope'):export(folder,path,version='SECRET_LABEL')
            with self.assertRaisesRegex(ValueError,'invalid_export_scope'):export(folder,path,platform='SECRET_PLATFORM')
            self.assertFalse(path.exists())


class ExternalChecks(unittest.TestCase):
    def test_recording_requires_terminal_and_cannot_relabel_decision(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)
            append_record(state,{'event':'decision_created','decision_id':'d','product_version':'0.8.1','time':1})
            args=(state,'d','eval-1','fixture-1','check-1','candidate','passed','synthetic')
            with self.assertRaisesRegex(ValueError,'not_terminal'):record_check(*args)
            append_record(state,{'event':'decision_completed','decision_id':'d','status':'completed','time':2})
            record_check(*args)
            with self.assertRaisesRegex(ValueError,'conflict'):record_check(state,'d','eval-1','fixture-1','check-1','baseline','passed','synthetic')
            out=state/'out.zip'; summary=export(state,out,version='0.8.1')
            self.assertEqual(summary['objective_checks']['decisions_with_checks'],1)
            self.assertEqual(summary['objective_checks']['quality_status'],'not_evaluated')

    def test_matched_results_require_same_checks_and_one_run_per_arm(self):
        rows=[]
        for arm in ('baseline','candidate'):
            rows += [{'event':'decision_created','decision_id':arm},
                     {'event':'decision_completed','decision_id':arm,'status':'completed'},
                     {'event':'outcome_check','decision_id':arm,'evaluation_id':'e','workload_id':'w',
                      'evaluation_arm':arm,'workload_origin':'synthetic','check_id':'c','check_result':'passed','check_source':'external_reported'}]
        result=evaluate_checks(rows)
        self.assertEqual(result['matched_workloads'],1)
        self.assertEqual(result['quality_status'],'matched_descriptive')
        self.assertFalse(result['causal_savings_demonstrated'])
        with_classifier=rows+[{'event':'engine_comparison','decision_id':'baseline','engine_active':True,'routing_engine':'jev'}]
        metrics=evaluate_checks(with_classifier)['matched_results'][0]['baseline_metrics']
        self.assertEqual(metrics['classifier_metric_coverage'],0)
        self.assertEqual(metrics['classifier_active_comparisons'],1)
        mismatched=[dict(r,check_id='different') if r.get('evaluation_arm')=='candidate' else r for r in rows]
        self.assertEqual(evaluate_checks(mismatched)['matched_workloads'],0)
        self.assertEqual(evaluate_checks([r for r in rows if r.get('event')!='outcome_check'])['decisions_with_checks'],0)


if __name__ == '__main__': unittest.main()
