import json
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import candidate_policy as cp
from decision_engines import candidate_routes, choice_confidence, run_jev
from model_catalog import DEFAULT_ROUTES
from router import Router
from state_store import read_records, append_record, atomic_json
from trial_evaluation import attempt_metrics, evaluate_trials, record_attempt
from evidence import scrub
from policy_control import configure
from tests.run_policy_trials import check_answer, mcp_overrides, accepted_route, await_telemetry

CATALOG={r['model']:{'low','medium','high','xhigh','max'} for r in DEFAULT_ROUTES.values()}


class CandidatePolicyTests(unittest.TestCase):
    def test_focused_code_is_eligible_for_luna_high_and_sol_not_astra(self):
        assessment=cp.profile('Añade un campo al formulario existente con su prueba unitaria.')
        choices=cp.candidates(DEFAULT_ROUTES,CATALOG,assessment)
        self.assertEqual(assessment['work_class'],'bounded')
        self.assertIn(('gpt-6-luna','high'),{(r['model'],r['effort']) for r in choices.values()})
        self.assertNotIn('gpt-6-astra',{r['model'] for r in choices.values()})
        self.assertEqual(candidate_routes(DEFAULT_ROUTES,CATALOG,assessment),choices)

    def test_visual_depth_length_and_attachment_do_not_impose_astra(self):
        for text in ('Rediseña toda la UX de la aplicación.', 'Refactoriza por completo el módulo de fechas.',
                     'Investiga una revisión profunda de la prueba que falla.', 'Extrae las cifras del CSV adjunto.',
                     'Analiza esta implementación '+('dato '*2200)):
            with self.subTest(text=text[:30]):
                a=cp.profile(text,{'present':True})
                r=cp.local_route(a,cp.candidates(DEFAULT_ROUTES,CATALOG,a))
                self.assertNotEqual(r['model'],'gpt-6-astra')

    def test_risk_is_retained_in_followup_but_new_task_is_independent(self):
        a=cp.profile('Investiga pérdida de datos en producción.')
        contract=cp.next_contract({},a)
        self.assertTrue(contract['risk_active'])
        self.assertEqual(cp.profile('Adelante',contract=contract)['work_class'],'critical')
        self.assertEqual(cp.profile('Solo queda documentar',contract=contract)['work_class'],'critical')
        self.assertFalse(cp.profile('Nueva tarea: traduce hola',contract=contract)['risk_active'])
        self.assertEqual(cp.profile('Adelante',context={'work_floor':'critical'})['work_class'],'critical')
        legacy=cp.profile('Adelante',context={'work_floor':'critical'})
        self.assertEqual(cp.profile('Adelante',contract=cp.next_contract({},legacy))['work_class'],'critical')

    def test_infrastructure_is_not_model_failure_and_feedback_not_double_counted(self):
        self.assertEqual(cp.failure_kind({'error_type':'timeout'},True),'infrastructure')
        self.assertEqual(cp.failure_kind({'model':'gpt-6.1-sol'}),'none')
        self.assertEqual(cp.failure_kind({},True),'external_check')
        a=cp.profile('Sigue fallando',contract={'remaining_class':'bounded'},failure='infrastructure')
        self.assertEqual(a['work_class'],'bounded')
        a=cp.profile('Sigue fallando',contract={'remaining_class':'bounded'},failure='external_check')
        c=cp.next_contract({},a,'decision-1')
        self.assertEqual(cp.next_contract(c,a,'decision-1')['quality_failures'],1)
        self.assertEqual(cp.next_contract(c,a,'decision-2')['quality_failures'],2)

    def test_catalog_must_not_invent_efforts_or_available_models(self):
        a=cp.profile('Corrige una función acotada.')
        self.assertIsNone(cp.local_route(a,cp.candidates(DEFAULT_ROUTES,{},a)))
        choices=cp.candidates(DEFAULT_ROUTES,{'gpt-6.1-sol':{'medium'}},a)
        self.assertEqual(cp.local_route(a,choices)['model'],'gpt-6.1-sol')

    def test_multiple_phases_do_not_start_in_luna_with_a_blocked_sol_transition(self):
        a=cp.profile('Corrige una función acotada y después integra los servicios.')
        self.assertEqual(cp.local_route(a,cp.candidates(DEFAULT_ROUTES,CATALOG,a))['model'],'gpt-6.1-sol')

    def test_unreviewed_wrong_build_or_incomplete_receipt_never_activates(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg={'policy_mode':'validated','policy_classes':['bounded']}
            self.assertFalse(cp.enabled_classes(cfg,folder,'a'*16))
            proof={'candidate_policy_version':9,'router_build_id':'a'*16,'quality_source':'executed_fixture_checks',
                'classes':{'bounded':{'held_out_pairs':2,'quality_regressions':0,'candidate_all_checks_passed':True,
                    'consumption_coverage_complete':True,'lower_consumption_per_success':True}}}
            atomic_json(Path(folder)/'policy-validation.json',proof)
            self.assertEqual(cp.enabled_classes(cfg,folder,'a'*16),{'bounded'})
            self.assertFalse(cp.enabled_classes(cfg,folder,'b'*16))
            proof['classes']['bounded']['consumption_coverage_complete']=False
            atomic_json(Path(folder)/'policy-validation.json',proof)
            self.assertFalse(cp.enabled_classes(cfg,folder,'a'*16))

    def test_compare_preserves_actual_reference_request_and_respects_explicit_manual(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); config=root/'config.json'
            results=[]
            for mode in ('reference','compare','validated'):
                config.write_text(json.dumps({'enabled':True,'routes':DEFAULT_ROUTES,'routing_engine':'rules','policy_mode':mode,'policy_classes':['bounded']}))
                r=Router(config,root/mode); r.catalog=CATALOG
                r.threads['t']={'provider':'openai','model':'gpt-6.1-sol','effort':'medium'}
                raw=json.dumps({'id':1,'method':'turn/start','params':{'threadId':'t','model':'gpt-6.1-sol',
                    'input':[{'type':'text','text':'Añade un campo al formulario existente con su prueba unitaria.'}]}}).encode()
                out=json.loads(r.route_turn(json.loads(raw),raw))
                results.append((out['params']['model'],out['params']['effort']))
                events=list(read_records(r.state_dir/'history.jsonl'))
                self.assertEqual(any(x['event']=='policy_comparison' for x in events),mode!='reference')
                explicit=json.dumps({'id':2,'method':'turn/start','params':{'threadId':'t','input':[{'type':'text','text':'Usa Astra: revisa este botón.'}]}}).encode()
                self.assertEqual(json.loads(r.route_turn(json.loads(explicit),explicit))['params']['model'],'gpt-6-astra')
                with patch('router.read_mode',return_value='manual'):
                    self.assertEqual(r.route_turn(json.loads(raw),raw),raw)
            self.assertEqual(len(set(results)),1)

    def test_verified_category_uses_shared_candidates_but_pending_boundary_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); config=root/'config.json'
            config.write_text(json.dumps({'enabled':True,'routes':DEFAULT_ROUTES,'policy_mode':'validated','policy_classes':['bounded']}))
            r=Router(config,root/'state'); r.catalog=CATALOG
            r.threads['t']={'provider':'openai','model':'gpt-6.1-sol','effort':'medium'}
            def start(text):
                message={'id':1,'method':'turn/start','params':{'threadId':'t','model':'gpt-6.1-sol','input':[{'type':'text','text':text}]}}
                return json.loads(r.route_turn(message,json.dumps(message).encode()))
            with patch('router.candidate_policy.enabled_classes',return_value={'bounded'}):
                out=start('Corrige una función acotada.')
                self.assertEqual(out['params']['model'],'gpt-6-luna')
                events=list(read_records(r.state_dir/'history.jsonl'))
                created=next(x for x in events if x['event']=='decision_created')
                self.assertEqual(created['routing_policy_version'],9)
                r.threads['t'].update(pending_phase_floor='critical',pending_phase_id='phase-1')
                out=start('Adelante')
                self.assertEqual(out['params']['model'],'gpt-6-astra')

    def test_policy_control_preserves_config_and_failed_activation_is_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path=root/'config.local.json'
            config={'routes':DEFAULT_ROUTES,'private_value':'synthetic-preserve','jev':{'timeout_ms':1000}}
            path.write_text(json.dumps(config))
            with patch('policy_control.router_identity',return_value='a'*16):
                configure(root,'compare')
                saved=path.read_bytes()
                self.assertEqual(json.loads(saved)['private_value'],config['private_value'])
                with self.assertRaises(ValueError):configure(root,'validated',['bounded'])
                self.assertEqual(path.read_bytes(),saved)
                with self.assertRaises(ValueError):configure(root,'compare',[True])
                self.assertEqual(path.read_bytes(),saved)

    def test_pilot_requires_exact_result_route_and_disables_known_mcp_names(self):
        self.assertFalse(check_answer('{"x":true}',{'expected':{'x':1}})['expected_result'])
        self.assertFalse(check_answer('{"x":1,"x":2}',{'expected':{'x':2}})['json_contract'])
        chosen={'model':'gpt-6-luna','effort':'high'}
        self.assertFalse(accepted_route([{'event':'decision_accepted','accepted_model':'gpt-6-astra','accepted_effort':'high'}],chosen))
        result=mcp_overrides('[mcp_servers.atlas]\n[mcp_servers."safe-name".env]\n[mcp_servers.\'literal\']')
        self.assertEqual(len(result),3)
        self.assertTrue(all(v is False for v in result.values()))
        self.assertEqual(mcp_overrides('[mcp_servers] # parent\n# empty\n\n[mcp_servers.safe]\nurl="ignored"'),
                         {'mcp_servers.safe.enabled':False})
        with self.assertRaises(ValueError):mcp_overrides('[mcp_servers."server.with.dots"]')
        for text in ('[mcp_servers]\na={}', 'mcp_servers = { a = {} }'):
            with self.assertRaises(ValueError):mcp_overrides(text)

    def test_pilot_waits_for_delayed_telemetry_before_archiving(self):
        terminal=[{'event':'decision_completed','thread':'t'}]
        drained=terminal+[{'event':'inference_observed','thread':'t'}]
        with patch('tests.run_policy_trials.read_records',side_effect=[terminal,drained]), \
             patch('tests.run_policy_trials.time.sleep') as sleep:
            self.assertEqual(await_telemetry(Path('unused'),'t'),drained)
            sleep.assert_called_once_with(.2)


class ConfidenceTests(unittest.TestCase):
    def test_probability_never_substitutes_confidence_and_precision_is_raw(self):
        self.assertIsNone(choice_confidence({}, {'choice':'x','probabilities':{'x':1}}))
        self.assertEqual(choice_confidence({}, {'confidence':.94999}),.94999)
        self.assertEqual(choice_confidence({'providerMetadata':{'typesafe':{'confidence':{'route':.8}}}}, {'confidence':.9}),.8)
        for v in (True,False,'0.99',float('nan'),float('inf'),-1,2):
            self.assertIsNone(choice_confidence({}, {'confidence':v}))
        result={'status':'ok','route':{'model':'x'},'confidence':.94999}
        self.assertFalse(cp.accepted_jev(result,{}))
        self.assertFalse(cp.accepted_jev(result,{'candidate_confidence_threshold':.95}))

    @patch('decision_engines.jev_key',return_value='synthetic')
    @patch('decision_engines._post_json')
    def test_candidate_jev_can_abstain_and_extract_provider_cost(self,post,key):
        a=cp.profile('Corrige una función acotada.')
        choices=cp.candidates(DEFAULT_ROUTES,CATALOG,a)
        post.return_value={'answers':{'route':{'choice':'abstain','confidence':.4}},
            'providerMetadata':{'gateway':{'cost':'0.0001'}},'usage':{'inputTokens':100}}
        r=run_jev({'jev':{'connection':'vercel'}},'',dict(a,task='synthetic'),choices)
        self.assertEqual(r['status'],'abstained')
        self.assertNotIn('route',r)
        self.assertEqual(r['engine_provider_cost_usd'],.0001)
        self.assertNotIn('Terra cubre',post.call_args.args[1]['questions']['route']['instructions'])


def cost_rows(decision,model='gpt-6-luna',status='completed',arm='candidate',index=1):
    return [
        {'event':'decision_created','decision_id':decision,'time':0},
        {'event':'decision_usage_baseline','decision_id':decision,**{'usage_baseline_'+k:0 for k in ('inputTokens','cachedInputTokens','outputTokens')}},
        {'event':'decision_usage_total','decision_id':decision,'native_total_inputTokens':100,'native_total_cachedInputTokens':0,'native_total_outputTokens':10},
        {'event':'inference_observed','decision_id':decision,'inference_event_id':decision+'-response','evidence_confidence':'confirmed',
            'observed_model':model,'inference_input_tokens':100,'inference_cached_tokens':0,'inference_output_tokens':10},
        {'event':'decision_completed','decision_id':decision,'status':status,'time':2},
        {'event':'outcome_check','decision_id':decision,'check_id':'result','check_result':'passed' if status=='completed' else 'failed','check_source':'external_reported'},
        {'event':'trial_attempt','decision_id':decision,'evaluation_id':'eval','workload_id':'fixture','trial_run_id':'run',
            'evaluation_arm':arm,'workload_origin':'synthetic','attempt_index':index,'trial_required_checks':['result'],'trial_split':'held_out'}]


class TrialTests(unittest.TestCase):
    def test_duplicate_snapshots_do_not_add_cost_and_incomplete_identity_stays_unknown(self):
        rows=cost_rows('d'); rows.extend([dict(rows[2]),dict(rows[3])])
        metrics=attempt_metrics(rows)
        self.assertTrue(metrics['consumption_coverage_complete'])
        self.assertAlmostEqual(metrics['estimated_standard_credits'],.000375)
        rows[3]['evidence_confidence']='probable'; rows[-1]['evidence_confidence']='probable'
        self.assertIsNone(attempt_metrics(rows)['estimated_standard_credits'])
        rows=cost_rows('d'); rows[2]['native_total_inputTokens']=200
        self.assertFalse(attempt_metrics(rows)['consumption_coverage_complete'])

    def test_failed_attempts_and_shadow_classifier_costs_count(self):
        rows=cost_rows('b','gpt-6.1-sol',arm='baseline')+cost_rows('c1',status='failed')+cost_rows('c2',index=2)
        rows.append({'event':'policy_comparison_jev','decision_id':'c1','routing_engine':'jev',
            'engine_comparison_id':'call-1','engine_provider_cost_usd':.001})
        row=evaluate_trials(rows)['results'][0]
        self.assertEqual(row['candidate']['attempts'],2)
        self.assertTrue(row['candidate']['passed'])
        self.assertAlmostEqual(row['candidate']['estimated_standard_credits'],.00075)
        self.assertEqual(row['candidate']['classifier_provider_reported_usd'],.001)
        rows[-1].pop('engine_provider_cost_usd')
        self.assertFalse(evaluate_trials(rows)['results'][0]['candidate']['consumption_coverage_complete'])

    def test_missing_attempts_or_different_checks_are_excluded(self):
        rows=cost_rows('b',arm='baseline')+cost_rows('c',index=2)
        self.assertEqual(evaluate_trials(rows)['excluded']['missing_or_repeated_attempt'],1)
        rows[-1]['attempt_index']=1; rows[-1]['trial_required_checks']=['other']
        self.assertEqual(evaluate_trials(rows)['excluded']['different_check_sets'],1)

    def test_bound_attempts_are_terminal_and_immutable_and_exports_preserve_check_join(self):
        with tempfile.TemporaryDirectory() as folder:
            for r in cost_rows('d')[:-1]:append_record(folder,r)
            args=(folder,'d','eval','fixture','run','candidate',1,'synthetic',['result'],'held_out')
            record_attempt(*args)
            with self.assertRaisesRegex(ValueError,'already_bound'):record_attempt(*args)
            row=scrub(list(read_records(Path(folder)/'history.jsonl'))[-1],b'key')
            check=scrub({'event':'outcome_check','check_id':'result'},b'key')
            self.assertEqual(row['trial_required_checks'],[check['check_id']])
            self.assertNotIn('fixture',json.dumps(row))

    def test_frozen_fixtures_are_30_with_separate_held_out_and_never_auto_activate(self):
        path=Path(__file__).with_name('policy_trial_fixtures.json')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'29e592e34c1d21403bae6cec22fe060ab2c90de6b5fb6d3ef828064b60cd0102')
        data=json.loads(path.read_text())
        self.assertEqual(len(data['fixtures']),30)
        self.assertEqual(sum(r['split']=='held_out' for r in data['fixtures']),12)
        self.assertFalse(data['policy_activation_eligible'])
