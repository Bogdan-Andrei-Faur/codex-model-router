import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routing import DEFAULT_ROUTES, EFFORTS, classify, classify_agent_identity, select_route, select_route_details, summarize_response_context
from router import Router


def encode(value):
    return (json.dumps(value, ensure_ascii=False) + "\n").encode()


class RoutingPolicyTests(unittest.TestCase):
    def test_spanish_and_english_workloads(self):
        cases = [
            ("Traduce al ingles: Nos vemos mañana.", "simple"),
            ("Explica que hace esta funcion.", "normal"),
            ("Summarize this paragraph in one sentence.", "simple"),
            ("Corrige el color del boton y comprueba el resultado.", "normal"),
            ("Crea un formulario para dar de alta contactos.", "normal"),
            ("Arregla la validación del campo correo.", "normal"),
            ("Investiga una condición de carrera entre dos procesos.", "complex"),
            ("Diseña la arquitectura de una aplicación distribuida.", "complex"),
            ("Review this refactor across several repositories.", "complex"),
            ("Investiga la doble asignación de robots en producción y pérdida de datos.", "critical"),
            ("Investigate a race condition causing a production outage and data loss.", "critical"),
            ("Haz una auditoría de seguridad del sistema de autenticación.", "critical"),
            ("Describe el riesgo de la parada de emergencia del robot.", "critical"),
        ]
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(classify(prompt).tier, expected)

    def test_ambiguous_followups_use_sol_without_current_work_evidence(self):
        for prompt in ("Sí, hazlo", "Continúa", "¿Por qué ocurre?", "Ahora compruébalo"):
            self.assertEqual(classify(prompt, "critical").tier, "complex")
        self.assertEqual(classify("Nueva tarea: traduce hola al inglés", "critical").tier, "simple")

    def test_failure_escalates_and_attachments_have_floor(self):
        self.assertEqual(classify("Sigue fallando", "normal").tier, "complex")
        self.assertEqual(classify("Sigue fallando", "critical").tier, "critical")
        self.assertEqual(classify("Explica esta imagen", attachments=True).tier, "critical")

    def test_visual_quality_and_audits_get_astra(self):
        for prompt in ("Rediseña la UX del panel", "Analiza la interfaz y mejora su accesibilidad", "Haz una auditoría del repositorio", "Investiga a fondo la arquitectura completa"):
            self.assertEqual(classify(prompt).tier, "critical", prompt)
        small = classify("Cambia solo el color del texto de la interfaz")
        self.assertEqual((small.tier, small.effort), ("normal", "low"))

    def test_effort_is_independent_and_ultra_is_explicit(self):
        labels = ("Ligero", "Medio", "Alto", "Muy alto", "Máx.", "Ultra")
        for label, effort in zip(labels, EFFORTS):
            route, _ = select_route("Usa Astra con esfuerzo " + label + ": revisa la interfaz", DEFAULT_ROUTES)
            self.assertEqual(route, {"model": "gpt-6-astra", "effort": effort})
        for prompt in ("Explica qué significa razonamiento Ultra", "El usuario suele usar esfuerzo Ultra", 'Traduce: "Usa razonamiento Ultra"', "No uses esfuerzo Ultra"):
            self.assertNotEqual(select_route(prompt, DEFAULT_ROUTES)[0]["effort"], "ultra")
        self.assertEqual(classify("Continúa", "critical", previous_effort="max").effort, "high")
        self.assertEqual(classify("Crea un formulario", "simple").tier, "normal")
        self.assertEqual(classify("Sigue fallando", "critical", previous_effort="xhigh").effort, "max")

    def test_acknowledgements_and_status_do_not_inherit_expensive_work(self):
        for prompt in ("Parece que ahora si esta funcionando", "Ok, perfecto", "Gracias!", "It is working now."):
            with self.subTest(prompt=prompt):
                result = classify(prompt, "critical", previous_effort="max")
                self.assertEqual((result.tier, result.effort, result.request_kind), ("simple", "low", "acknowledgement"))
                self.assertIsNone(result.quality_floor)
        result = classify("Comprueba cuantas solicitudes de telemetria han llegado", "critical", previous_effort="max")
        self.assertEqual((result.tier, result.effort, result.request_kind), ("normal", "medium", "status_check"))

    def test_execution_followups_and_mixed_messages_keep_required_capacity(self):
        for prompt in ("Adelante, impleméntalo", "Ok, implementa lo que acordamos", "Vale, sigue con ello", "Ok, arréglalo"):
            with self.subTest(prompt=prompt):
                result = classify(prompt, "critical", previous_effort="max",
                                  response_context={"implementation_pending": True, "work_floor": "critical"})
                self.assertEqual((result.tier, result.quality_floor, result.request_kind), ("critical", "critical", "planned_followup"))
                self.assertFalse(result.max_effort_allowed)
        for prompt in ("Gracias, audita la autenticación", "Ahora funciona, investiga la pérdida de datos", "Check telemetry counters and audit authentication"):
            self.assertEqual(classify(prompt, "critical").quality_floor, "critical")
        self.assertEqual(classify("Ok, perfecto", "simple", attachments=True).quality_floor, "critical")
        self.assertEqual(classify("Ok, haz una auditoría exhaustiva de autenticación", "critical", previous_effort="high").effort, "max")

    def test_ambiguity_requires_analysis_but_does_not_force_astra(self):
        result = classify("Tengo una duda sobre esto")
        self.assertEqual(result.request_kind, "ambiguous")
        self.assertEqual(result.quality_floor, "complex")

    def test_independent_requests_do_not_inherit_pending_critical_work(self):
        context = {"implementation_pending": True, "work_floor": "critical"}
        for prompt in ("Cambia solo el color del texto", "Ok, implementa un formulario para contactos",
                       "Ahora añade una columna al listado", "Explica esta función", "¿Por qué ocurre?"):
            with self.subTest(prompt=prompt):
                result = classify(prompt, "critical", previous_effort="xhigh", response_context=context)
                self.assertNotEqual(result.quality_floor, "critical")
                self.assertNotIn(result.request_kind, ("planned_followup", "work_followup"))
        for prompt in ("Implementa lo acordado", "Sigue con lo que falta", "Ahora compruébalo", "Ok, hazlo"):
            with self.subTest(prompt=prompt):
                self.assertEqual(classify(prompt, "normal", response_context=context).quality_floor, "critical")
        self.assertEqual(classify("Ahora arregla la autenticación", "normal", response_context=context).quality_floor, "complex")

    def test_previous_response_summary_turns_confirmation_into_planned_followup(self):
        context = summarize_response_context("He preparado el plan de implementación en tres pasos. Cuando digas adelante, implemento el cambio y ejecuto las pruebas.")
        self.assertEqual(context["response_kind"], "plan")
        result = classify("Adelante", "normal", previous_effort="medium", response_context=context)
        self.assertEqual((result.request_kind, result.quality_floor), ("planned_followup", "normal"))

    def test_pending_points_in_response_set_the_next_turn_minimum(self):
        context = summarize_response_context("Quedan cuatro puntos pendientes: integrar el proveedor, corregir el estado, añadir pruebas y validar la migración.")
        self.assertEqual((context["response_kind"], context["work_floor"]), ("pending_work", "complex"))
        result = classify("Adelante", "simple", previous_effort="low", response_context=context)
        self.assertEqual((result.tier, result.quality_floor, result.request_kind), ("complex", "complex", "planned_followup"))
        route, reasons = select_route_details("Adelante", DEFAULT_ROUTES, "simple", "low", response_context=context)
        self.assertEqual(route, {"model": "gpt-5.6-sol", "effort": "high"})
        self.assertEqual(reasons["quality_floor"], "complex")
        reset = classify("Nueva tarea: traduce hola al inglés", "simple", previous_effort="low", response_context=context)
        self.assertEqual((reset.tier, reset.quality_floor), ("simple", None))

    def test_model_and_effort_explanations_are_separate(self):
        route, reasons = select_route_details("Rediseña a fondo la UX del panel", DEFAULT_ROUTES)
        self.assertEqual(route, {"model": "gpt-6-astra", "effort": "xhigh"})
        self.assertIn("interfaces", reasons["model"])
        self.assertIn("profunda", reasons["effort"])
        route, reasons = select_route_details("Usa Sol con esfuerzo Ligero: revisa esto", DEFAULT_ROUTES)
        self.assertEqual(reasons["source"], "explicit")
        self.assertIn("modelo indicado", reasons["model"])
        self.assertIn("nivel de razonamiento indicado", reasons["effort"])

    def test_agent_identity_uses_title_message_and_safe_fallbacks(self):
        cases = [
            ("", "Rediseña la UX de la cápsula", False, None, "interface", "alta"),
            ("Auditar permisos", "Sí, continúa", False, "interface", "audit", "alta"),
            ("", "Escribe pruebas E2E y valida el formulario", False, None, "tests", "alta"),
            ("", "", True, None, "interface", "baja"),
            ("", "Sí, hazlo", False, "architecture", "architecture", "heredada"),
            ("", "Sí, hazlo", False, None, "general", "baja"),
        ]
        for title, message, attachments, previous, category, confidence in cases:
            with self.subTest(title=title, message=message):
                self.assertEqual(classify_agent_identity(message, title, attachments, previous=previous), (category, confidence))


class ProtocolTests(unittest.TestCase):
    def test_manual_mode_is_persistent_scoped_and_preserves_exact_request(self):
        from task_modes import mode_path, read_mode
        from desktop import atomic_json
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        target=mode_path(self.router.state_dir,'t')
        atomic_json(target,{'schema':1,'thread':'t','mode':'manual'})
        raw=encode(self.request())
        self.assertEqual(self.router.client_line(raw),raw)
        self.assertEqual(self.router.accepted_routes[7]['source'],'manual')
        self.assertEqual(read_mode(self.router.state_dir,'another-task'),'automatic')
        restarted=Router(self.path,self.router.state_dir)
        restarted.catalog=self.router.catalog
        restarted.threads['t']={'provider':'openai','model':'gpt-6-astra','seen_turn':False}
        self.assertEqual(restarted.client_line(raw),raw)
        # Switching mode affects only future requests, not the pending turn.
        atomic_json(target,{'schema':1,'thread':'t','mode':'automatic'})
        self.assertEqual(restarted.client_line(raw),raw)
        restarted.server_line(encode({'id':7,'result':{'turn':{'id':'turn'}}}))
        self.path.write_text(json.dumps({'enabled':True,'routes':DEFAULT_ROUTES}))
        self.assertEqual(json.loads(restarted.client_line(raw))['params']['model'],'gpt-5.6-luna')

    def test_damaged_task_preference_cannot_reenable_routing(self):
        from task_modes import mode_path, read_mode
        target=mode_path(self.router.state_dir,'t');target.parent.mkdir(parents=True)
        for contents in ('bad-json','[]','{"mode":"automatic","thread":"someone-else"}'):
            target.write_text(contents)
            self.assertEqual(read_mode(self.router.state_dir,'t'),'manual')
        self.assertEqual(self.router.client_line(encode(self.request())),encode(self.request()))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}))
        self.router = Router(self.path, Path(self.tmp.name) / "state")
        self.router.catalog = {x["model"]: set(EFFORTS) for x in DEFAULT_ROUTES.values()}
        self.router.catalog["gpt-5.6-luna"].remove("ultra")
        self.router.threads["t"] = {"provider": "openai", "model": "gpt-6-astra", "seen_turn": False}

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, prompt="Traduce hola al ingles", **params):
        return {"id": 7, "method": "turn/start", "params": {
            "threadId": "t", "model": "gpt-6-astra", "effort": "ultra",
            "input": [{"type": "text", "text": prompt}], **params}}

    def test_only_model_and_effort_change(self):
        original = self.request("Analiza estos adjuntos", input=[
            {"type": "text", "text": "Analiza estos adjuntos", "text_elements": [{"byteRange": {"start": 0, "end": 1}, "placeholder": "x"}]},
            {"type": "localImage", "path": r"C:\mis fotos\ángulo.png"},
            {"type": "image", "url": "data:image/png;base64,c2VjcmV0"},
            {"type": "mention", "name": "Documento", "path": "plugin://attached-resource"}],
            approvalPolicy="on-request", permissions="read-only", cwd=r"C:\proyecto",
            dynamicUnknown={"future": [1, 2]}, outputSchema={"type": "object"},
            collaborationMode={"mode": "plan", "settings": {
                "model": "gpt-6-astra", "reasoning_effort": "ultra", "developer_instructions": "Keep these"}})
        expected = copy.deepcopy(original)
        expected["params"]["model"] = "gpt-6-astra"
        expected["params"]["effort"] = "high"
        expected["params"]["collaborationMode"]["settings"].update(
            model="gpt-6-astra", reasoning_effort="high")
        self.assertEqual(json.loads(self.router.client_line(encode(original))), expected)

    @patch("router.run_jev")
    def test_jev_engine_can_select_a_valid_pair_and_keeps_telemetry_content_free(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        fake_jev.return_value = {"engine": "jev", "status": "ok", "latency_ms": 25, "confidence": .91,
                                 "engine_model": "jev-test", "route": {"model": "gpt-5.6-terra", "effort": "medium", "tier": "normal", "label": "Terra · medium"}}
        result = json.loads(self.router.client_line(encode(self.request("PRIVATE_JEV_SENTINEL implementa un cambio concreto"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-terra", "medium"))
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        self.assertEqual(records[-1]["routing_engine"], "jev")
        self.assertNotIn("PRIVATE_JEV_SENTINEL", (Path(self.tmp.name) / "state" / "history.jsonl").read_text())

    @patch("router.run_jev")
    def test_jev_can_reduce_effort_while_continuing_complex_work(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-6-astra", effort="max", tier="critical", seen_turn=True)
        self.router.threads["t"]["task_contract"] = {"version": 2, "status": "pending", "floor": "critical"}
        fake_jev.return_value = {"engine": "jev", "status": "ok", "latency_ms": 25, "confidence": .91,
                                 "engine_model": "jev-test", "continuity_strategy": "continue",
                                 "route": {"model": "gpt-6-astra", "effort": "high", "tier": "critical", "label": "Astra · high"}}
        result = json.loads(self.router.client_line(encode(self.request("Vale, sigue con ello", effort="high"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-6-astra", "high"))
        self.assertIn("Jev continuó la tarea", self.router.threads["t"]["model_reason"])
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        self.assertEqual(records[0]["continuity_strategy"], "continue")
        fake_jev.assert_called_once()

    @patch("router.run_jev")
    def test_jev_continuation_does_not_override_a_lightweight_route(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-6-astra", effort="max", tier="critical", seen_turn=True,
                                      name="Auditoría de seguridad", agent_category="audit")
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-terra", "effort": "medium", "label": "Terra · medium"}}
        result = json.loads(self.router.client_line(encode(self.request("Parece que ahora si esta funcionando"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-terra", "medium"))
        policy, candidates = fake_jev.call_args.args[2:4]
        self.assertEqual(policy["request_kind"], "acknowledgement")
        self.assertIsNone(policy["quality_floor"])
        self.assertTrue(all(r["tier"] in ("simple", "normal") and r["effort"] in ("low", "medium") for r in candidates.values()))
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        self.assertEqual(records[0]["routing_policy_version"], 7)
        self.assertEqual(records[0]["request_kind"], "acknowledgement")
        self.assertNotIn("Parece que ahora", str(records))

    @patch("router.run_jev")
    def test_jev_cannot_downgrade_ambiguity_to_luna_or_force_astra_from_title(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(name="Auditoría de seguridad", agent_category="audit")
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "reassess",
                                "route": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low"}}
        result = json.loads(self.router.client_line(encode(self.request("Tengo una duda sobre esto"))))
        self.assertEqual(result["params"]["model"], "gpt-5.6-sol")
        self.assertEqual(fake_jev.call_args.args[2]["quality_floor"], "complex")
        self.assertEqual({r['tier'] for r in fake_jev.call_args.args[3].values()}, {'complex'})

    @patch("router.run_jev")
    def test_jev_cannot_force_maximum_for_an_acknowledgement(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-6-astra", effort="max", tier="critical", seen_turn=True)
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-6-astra", "effort": "max", "label": "Astra · max"}}
        result = json.loads(self.router.client_line(encode(self.request("Parece que ahora si esta funcionando"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-luna", "low"))
        self.assertEqual(self.router.threads["t"]["engine_status"], "guardrail")
        self.assertEqual(self.router.threads["t"]["routing_engine"], "rules")

    @patch("router.run_jev")
    def test_jev_cannot_drop_the_capacity_of_work_it_is_asked_to_resume(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-6-astra", effort="max", tier="critical", seen_turn=True)
        self.router.threads["t"]["task_contract"] = {"version": 2, "status": "pending", "floor": "critical"}
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-luna", "effort": "low"}}
        result = json.loads(self.router.client_line(encode(self.request("Adelante, impleméntalo"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-6-astra", "xhigh"))
        self.assertEqual(self.router.threads["t"]["engine_status"], "guardrail")

    @patch("router.run_jev")
    def test_jev_outage_uses_lightweight_fallback_for_confirmation(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-6-astra", effort="max", tier="critical", seen_turn=True)
        fake_jev.return_value = {"engine": "jev", "status": "unavailable", "engine_failure": "rate_limited"}
        result = json.loads(self.router.client_line(encode(self.request("Parece que ahora si esta funcionando"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-luna", "low"))
        self.assertEqual(self.router.threads["t"]["routing_engine"], "rules")

    @patch("router.run_jev")
    def test_response_plan_is_sent_as_metadata_for_brief_confirmation(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.threads["t"].update(model="gpt-5.6-terra", effort="medium", tier="normal", seen_turn=True,
                                      response_context={"has_plan": True, "implementation_pending": True,
                                                        "mentions_tests": True, "mentions_deployment": False,
                                                        "risk_signals": False, "response_kind": "plan", "work_floor": "normal"})
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-terra", "effort": "medium", "label": "Terra · medium"}}
        result = json.loads(self.router.client_line(encode(self.request("Adelante"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-terra", "medium"))
        state = fake_jev.call_args.args[2]
        self.assertEqual(state["previous_response_context"]["response_kind"], "plan")
        self.assertTrue(state["previous_response_context"]["mentions_tests"])

    @patch("router.run_jev")
    def test_pending_points_prevent_jev_from_selecting_luna(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        context = summarize_response_context("Faltan varios puntos: integrar los cambios entre servicios, corregir el flujo y validar las pruebas.")
        self.router.threads["t"].update(model="gpt-5.6-luna", effort="low", tier="simple", seen_turn=True, response_context=context)
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low"}}
        result = json.loads(self.router.client_line(encode(self.request("Adelante"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-sol", "high"))
        self.assertEqual(self.router.threads["t"]["engine_status"], "guardrail")
        state, candidates = fake_jev.call_args.args[2:4]
        self.assertEqual(state["previous_response_context"]["work_floor"], "complex")
        self.assertTrue(all(route["tier"] in ("complex", "critical") for route in candidates.values()))

    @patch("router.run_jev")
    def test_pending_tests_keep_floor_for_elliptical_followup_after_luna(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        context = summarize_response_context("Todavía quedan cambios por hacer y después hay que ejecutar las pruebas.")
        self.router.threads["t"].update(model="gpt-5.6-luna", effort="low", tier="simple",
                                        seen_turn=True, response_context=context)
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low"}}
        result = json.loads(self.router.client_line(encode(self.request("Haz lo que consideres necesario para dejarlo bien."))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-sol", "high"))
        state, candidates = fake_jev.call_args.args[2:4]
        self.assertEqual((state["request_kind"], state["quality_floor"]), ("planned_followup", "complex"))
        self.assertTrue(all(route["tier"] in ("complex", "critical") for route in candidates.values()))

    @patch("router.run_jev")
    def test_jev_cannot_reduce_a_research_quality_floor(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        fake_jev.return_value = {"engine": "jev", "status": "ok", "latency_ms": 25, "confidence": .91,
                                 "engine_model": "jev-test", "route": {"model": "gpt-5.6-luna", "effort": "low", "tier": "simple", "label": "Luna · low"}}
        result = json.loads(self.router.client_line(encode(self.request("Investiga una condición de carrera entre servicios"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-sol", "high"))
        state = fake_jev.call_args.args[2]
        self.assertEqual(state["quality_floor"], "complex")

    def test_non_turn_messages_are_byte_identical(self):
        for data in [b'  {"id":9, "method":"turn/interrupt", "params":{"threadId":"t","turnId":"q"}} \n',
                     b'{"id":7,"result":{"decision":"approved"}}\n', b'not json\n', b'[1,2]\n']:
            self.assertEqual(self.router.client_line(data), data)

    def test_interrupt_terminates_only_native_process_registered_for_exact_turn(self):
        self.router.server_line(encode({"method": "item/started", "params": {
            "threadId": "t", "turnId": "q", "item": {
                "id": "command-q", "type": "commandExecution", "processId": "process-q"}}}))
        self.router.server_line(encode({"method": "item/started", "params": {
            "threadId": "t", "turnId": "other", "item": {
                "id": "command-other", "type": "commandExecution", "processId": "process-other"}}}))
        raw = encode({"id": 9, "method": "turn/interrupt", "params": {
            "threadId": "t", "turnId": "q"}})
        self.assertEqual(self.router.client_line(raw), raw)
        terminate = self.router.drain_outbound()
        self.assertEqual(len(terminate), 1)
        self.assertEqual(terminate[0]["method"], "thread/backgroundTerminals/terminate")
        self.assertEqual(terminate[0]["params"], {"threadId": "t", "processId": "process-q"})
        self.assertIn(("t", "other", "command-other"), self.router.commands.running)

    def test_active_turn_is_not_replayed_or_rerouted(self):
        self.router.server_line(encode({"method": "turn/started", "params": {"threadId": "t"}}))
        raw = encode(self.request())
        self.assertEqual(self.router.client_line(raw), raw)

    def test_completed_response_blocks_keep_only_pending_work_metadata(self):
        self.router.server_line(encode({"method": "item/completed", "params": {"threadId": "t", "item": {
            "type": "agentMessage", "content": [
                {"text": "PRIVATE_SENTINEL: quedan varios puntos pendientes para integrar los servicios y validar pruebas."}
            ]}}}))
        context = self.router.threads["t"]["response_context"]
        self.assertEqual((context["response_kind"], context["work_floor"]), ("pending_work", "complex"))
        history = self.router.state_dir / "history.jsonl"
        persisted = history.read_text(encoding="utf-8")
        self.assertIn('"event":"task_context"', persisted)
        self.assertIn('"task_floor":"complex"', persisted)
        self.assertNotIn("PRIVATE_SENTINEL", persisted)
        self.assertNotIn("PRIVATE_SENTINEL", str(context))

    def test_internal_ephemeral_root_keeps_native_settings_and_creates_no_decision(self):
        self.router.threads["helper"] = {"provider": "openai", "model": "gpt-5.6-luna",
                                          "effort": "low", "ephemeral": True, "parent": None}
        request = self.request("Generate a concise UI title", threadId="helper")
        raw = encode(request)
        self.assertEqual(self.router.client_line(raw), raw)
        self.assertNotIn("helper", self.router.pending)
        self.assertNotIn("helper", self.router.current_decisions)
        self.assertFalse((Path(self.tmp.name) / "state" / "history.jsonl").exists())
        self.assertEqual(self.router.threads["helper"]["model"], "gpt-5.6-luna")

    def test_pending_turn_does_not_reroute_a_second_message(self):
        self.router.client_line(encode(self.request()))
        raw = encode(self.request("Nueva tarea: investiga una migración"))
        self.assertEqual(self.router.client_line(raw), raw)

    def test_unknown_provider_or_model_is_preserved(self):
        for provider, model in [("other-service", "third-party-model"), (None, "gpt-6-astra"), ("openai", "future-new-model")]:
            with self.subTest(provider=provider, model=model):
                self.router.pending.clear()
                self.router.threads["t"]["provider"] = provider
                raw = encode(self.request(model=model))
                self.assertEqual(self.router.client_line(raw), raw)

    def test_unavailable_catalog_and_invalid_config_preserve_message(self):
        self.router.catalog = {}
        raw = encode(self.request())
        self.assertEqual(self.router.client_line(raw), raw)
        self.router.pending.clear()
        self.path.write_text("corrupted")
        self.assertEqual(self.router.client_line(raw), raw)

    def test_pause_is_immediate_without_restart(self):
        self.path.write_text('{"enabled": false}')
        raw = encode(self.request())
        self.assertEqual(self.router.client_line(raw), raw)

    def test_explicit_instruction_wins(self):
        result = json.loads(self.router.client_line(encode(self.request("Usa Astra: traduce hola"))))
        self.assertEqual(result["params"]["model"], "gpt-6-astra")

    def test_model_catalog_and_provider_learned_from_native_responses(self):
        router = self.router
        router.catalog.clear()
        router.threads.clear()
        router.client_line(encode({"id": 1, "method": "model/list", "params": {}}))
        # A server-side tool request may share a numeric id with our request.
        router.server_line(encode({"id": 1, "method": "item/tool/call", "params": {}}))
        self.assertIn(1, router.requests)
        router.server_line(encode({"id": 1, "result": {"data": [{"model": "gpt-5.6-luna",
            "supportedReasoningEfforts": [{"reasoningEffort": "low"}]}]}}))
        router.client_line(encode({"id": 2, "method": "thread/start", "params": {}}))
        router.server_line(encode({"id": 2, "result": {"thread": {"id": "t"},
            "modelProvider": "openai", "model": "gpt-6-astra"}}))
        result = json.loads(router.client_line(encode(self.request())))
        self.assertEqual(result["params"]["model"], "gpt-5.6-luna")

    def test_reopened_conversation_without_work_evidence_uses_sol_for_short_followup(self):
        self.router.client_line(encode({"id": 3, "method": "thread/resume", "params": {"threadId": "t"}}))
        self.router.threads.clear()
        self.router.server_line(encode({"id": 3, "result": {"thread": {"id": "t"},
            "modelProvider": "openai", "model": "gpt-6-astra"}}))
        result = json.loads(self.router.client_line(encode(self.request("Continúa"))))
        self.assertEqual(result["params"]["model"], "gpt-5.6-sol")

    def test_logs_contain_no_prompt_attachment_or_auth(self):
        self.router.client_line(encode(self.request("Traduce PRIVATE_SENTINEL password sk-not-real")))
        text = "".join(p.read_text() for p in (Path(self.tmp.name) / "state").glob("*.json"))
        self.assertNotIn("PRIVATE_SENTINEL", text)
        self.assertNotIn("sk-not-real", text)
        self.assertIn("gpt-5.6-luna", text)

    def test_prompt_dataset_is_exact_correlated_private_and_opt_in(self):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES,
                                         "prompt_logging": True, "history_days": 90}))
        prompt = "Analiza exactamente PROMPT_DATASET_SENTINEL"
        request = self.request(prompt, input=[{"type": "text", "text": prompt},
                                              {"type": "localImage", "path": "/private/image.png"}])
        self.router.client_line(encode(request))
        prompts = Path(self.tmp.name) / "state" / "prompts.jsonl"
        rows = [json.loads(line) for line in prompts.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["prompt"], prompt)
        self.assertEqual(row["decision_id"], self.router.current_decisions["t"])
        self.assertEqual((row["model"], row["effort"]),
                         (self.router.threads["t"]["requested_model"], self.router.threads["t"]["requested_effort"]))
        self.assertTrue(row["has_attachments"])
        self.assertEqual(row["routing_engine"], "rules")
        self.assertNotIn("/private/image.png", prompts.read_text(encoding="utf-8"))
        self.assertNotIn("PROMPT_DATASET_SENTINEL",
                         (Path(self.tmp.name) / "state" / "history.jsonl").read_text(encoding="utf-8"))
        if os.name != "nt":
            self.assertEqual(prompts.stat().st_mode & 0o777, 0o600)

    def test_prompt_dataset_also_captures_preserved_turns_when_enabled(self):
        self.path.write_text(json.dumps({"enabled": False, "routes": DEFAULT_ROUTES,
                                         "prompt_logging": True}))
        raw = encode(self.request("PRESERVED_PROMPT_SENTINEL"))
        self.assertEqual(self.router.client_line(raw), raw)
        row = json.loads((Path(self.tmp.name) / "state" / "prompts.jsonl").read_text(encoding="utf-8"))
        self.assertEqual((row["prompt"], row["source"]), ("PRESERVED_PROMPT_SENTINEL", "preserved"))

    def test_display_sync_uses_real_server_after_ack_and_hides_only_own_reply(self):
        self.router.client_line(encode(self.request()))
        self.assertEqual(self.router.drain_outbound(), [])
        self.assertTrue(self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}})))
        outgoing = self.router.drain_outbound()
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0]["method"], "thread/settings/update")
        self.assertEqual(outgoing[0]["params"], {"threadId": "t", "model": "gpt-5.6-luna", "effort": "low"})
        self.assertFalse(self.router.server_line(encode({"id": outgoing[0]["id"], "result": {}})))
        self.assertTrue(self.router.server_line(encode({"id": 123, "result": {}})))
        self.assertTrue(self.router.server_line(encode({"method": "thread/settings/updated", "params": {
            "threadId": "t", "threadSettings": {"model": "gpt-5.6-luna", "effort": "medium"}}})))

    def test_rejected_turn_does_not_send_display_sync_or_retry(self):
        self.router.client_line(encode(self.request()))
        self.router.server_line(encode({"id": 7, "error": {"code": -1, "message": "failed"}}))
        self.assertEqual(self.router.drain_outbound(), [])
        self.assertEqual(self.router.threads["t"]["confirmation"], "Rechazado")
        self.assertEqual(self.router.stats["accepted"], 0)

    def test_luna_ultra_falls_back_to_supported_max(self):
        result = json.loads(self.router.client_line(encode(self.request("Usa Luna con esfuerzo Ultra: traduce hola"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-luna", "max"))
        self.assertIn("Ultra no está disponible", self.router.threads["t"]["effort_reason"])

    def test_persistent_history_tracks_decision_lifecycle_without_content(self):
        self.router.client_line(encode(self.request("Traduce PRIVATE_HISTORY_SENTINEL al inglés")))
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.router.threads["t"]["tokens"] = {"inputTokens": 20, "outputTokens": 2}
        self.router.server_line(encode({"method": "turn/completed", "params": {
            "threadId": "t", "turn": {"status": "completed"}}}))
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        self.assertEqual([r["event"] for r in records],
                         ["decision_created", "engine_comparison", "decision_routed", "decision_accepted", "decision_completed"])
        self.assertEqual(len({r["decision_id"] for r in records}), 1)
        self.assertEqual(records[0]["source"], "automatic")
        self.assertIn("model_reason", records[0])
        self.assertIn("effort_reason", records[0])
        self.assertEqual(records[0]["agent_category"], "text")
        self.assertEqual(records[0]["agent_confidence"], "alta")
        self.assertEqual(records[1]["routing_engine"], "rules")
        self.assertEqual(records[1]["proposed_model"], "gpt-5.6-luna")
        self.assertEqual((records[2]["routing_engine"], records[2]["engine_applied"]), ("rules", False))
        self.assertEqual(records[-1]["inputTokens"], 20)
        self.assertNotIn("PRIVATE_HISTORY_SENTINEL", (Path(self.tmp.name) / "state" / "history.jsonl").read_text())

    def test_usage_is_persisted_live_and_new_decision_clears_previous_usage(self):
        self.router.client_line(encode(self.request()))
        self.router.server_line(encode({"method": "thread/tokenUsage/updated", "params": {
            "threadId": "t", "tokenUsage": {"last": {"inputTokens": 40, "outputTokens": 4}}}}))
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        self.assertEqual(records[-1]["event"], "decision_usage")
        self.assertEqual(records[-1]["inputTokens"], 40)
        first_id = self.router.current_decisions["t"]
        self.router.new_decision("t", "gpt-5.6-terra", "medium", "reason", "effort", "automatic")
        self.assertNotEqual(first_id, self.router.current_decisions["t"])
        self.assertNotIn("tokens", self.router.threads["t"])

    def test_failed_followup_marks_previous_decision_as_retry_signal(self):
        self.router.client_line(encode(self.request()))
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.router.server_line(encode({"method": "turn/completed", "params": {
            "threadId": "t", "turn": {"status": "completed"}}}))
        first_id = self.router.current_decisions["t"]
        request = self.request("Sigue fallando")
        self.router.client_line(encode(request))
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        signal = next(r for r in records if r["event"] == "decision_signal")
        self.assertEqual((signal["decision_id"], signal["signal"]), (first_id, "retry"))

    def test_monitor_keeps_accepted_turn_separate_from_next_settings(self):
        self.router.client_line(encode(self.request()))
        self.assertEqual(self.router.threads["t"]["phase_status"], "proposed")
        self.assertEqual(self.router.threads["t"]["phase_transition"], "blocked_astra_boundary")
        self.assertNotEqual(self.router.threads["t"].get("confirmation"), "Aceptado por Codex")
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.assertEqual(self.router.threads["t"]["phase_status"], "accepted")
        self.router.server_line(encode({"method": "thread/settings/updated", "params": {"threadId": "t", "threadSettings": {"model": "gpt-6-astra", "effort": "max"}}}))
        self.assertEqual(self.router.threads["t"]["model"], "gpt-5.6-luna")
        self.assertEqual(self.router.threads["t"]["effort"], "low")
        self.assertEqual(self.router.threads["t"]["confirmation"], "Aceptado por Codex")
        self.assertEqual(self.router.threads["t"]["phase_status"], "accepted")
        self.assertEqual(self.router.stats["accepted"], 1)
        self.assertEqual(self.router.stats["non_astra"], 1)
        self.assertEqual(self.router.stats["telemetry_confirmed"], 0)
        self.router.server_line(encode({"method": "turn/completed", "params": {"threadId": "t", "turn": {"status": "completed"}}}))
        self.assertEqual(self.router.threads["t"]["status"], "completed")
        self.assertEqual(self.router.threads["t"]["phase_status"], "completed")

    def test_late_picker_settings_do_not_regress_pipeline_or_claim_inference(self):
        self.router.client_line(encode(self.request()))
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.router.server_line(encode({"method": "turn/started", "params": {"threadId": "t"}}))
        settings = encode({"method": "thread/settings/updated", "params": {"threadId": "t",
                           "threadSettings": {"model": "gpt-6-astra", "effort": "max"}}})
        self.router.server_line(settings)
        self.assertEqual(self.router.threads["t"]["phase_status"], "active")
        self.assertEqual(self.router.threads["t"]["phase_model"], "gpt-5.6-luna")
        self.router.server_line(encode({"method": "turn/completed", "params": {
            "threadId": "t", "turn": {"status": "completed"}}}))
        self.router.server_line(settings)
        row = self.router.threads["t"]
        self.assertEqual(row["phase_status"], "completed")
        self.assertEqual(row["phase_pipeline"][1]["state"], "completed")
        self.assertNotIn("observed_model", row)
        records = [json.loads(line) for line in (self.router.state_dir / "history.jsonl").read_text().splitlines()]
        self.assertEqual(next(r for r in records if r["event"] == "decision_accepted")["phase_pipeline"][1]["state"], "accepted")
        self.assertEqual(records[-1]["phase_pipeline"][1]["state"], "completed")
        self.assertTrue(any(r["event"] == "phase_started" for r in records))

    def test_paused_turn_is_observed_without_changing_it(self):
        self.path.write_text('{"enabled": false}')
        raw = encode(self.request())
        self.assertEqual(self.router.client_line(raw), raw)
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.assertEqual(self.router.threads["t"]["model"], "gpt-6-astra")
        self.assertEqual(self.router.threads["t"]["effort"], "ultra")
        self.assertEqual(self.router.drain_outbound(), [])

    def test_agent_telemetry_does_not_copy_prompt_or_output(self):
        self.router.threads["t"].update(agent_category="architecture", agent_confidence="alta")
        self.router.server_line(encode({"method": "item/started", "params": {"threadId": "t", "item": {
            "type": "collabAgentToolCall", "senderThreadId": "t", "receiverThreadIds": ["child"],
            "model": "gpt-5.6-sol", "reasoningEffort": "high", "prompt": "SECRET_PROMPT",
            "agentsStates": {"child": {"status": "running", "message": "SECRET_RESULT"}}}}}))
        self.router.log({"event": "snapshot"})
        child = self.router.threads["child"]
        self.assertEqual((child["model"], child["parent"], child["confirmation"]), ("gpt-5.6-sol", "t", "Solicitado por agente"))
        self.assertEqual((child["agent_category"], child["agent_confidence"]), ("architecture", "heredada"))
        logged = next((Path(self.tmp.name) / "state").glob("*.json")).read_text()
        self.assertNotIn("SECRET_", logged)

    def test_agent_category_survives_router_restart_without_replaying_content(self):
        self.router.client_line(encode(self.request("Investiga la arquitectura distribuida del servicio")))
        restarted = Router(self.path, Path(self.tmp.name) / "state")
        restarted.catalog = {x["model"]: set(EFFORTS) for x in DEFAULT_ROUTES.values()}
        restarted.client_line(encode({"id": 8, "method": "thread/resume", "params": {"threadId": "t"}}))
        restarted.server_line(encode({"id": 8, "result": {"thread": {"id": "t", "name": "General"},
            "modelProvider": "openai", "model": "gpt-6-astra"}}))
        restarted.client_line(encode(self.request("Sí, continúa")))
        self.assertEqual(restarted.threads["t"]["agent_category"], "architecture")

    @patch("router.run_jev")
    def test_pending_work_floor_survives_restart_without_response_text(self, fake_jev):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "jev"}))
        self.router.server_line(encode({"method": "item/completed", "params": {"threadId": "t", "item": {
            "type": "agentMessage", "text": "PRIVATE_SENTINEL: todavía quedan cambios y hay que ejecutar las pruebas."
        }}}))
        self.assertEqual(self.router.threads["t"]["task_floor"], "complex")

        restarted = Router(self.path, Path(self.tmp.name) / "state")
        restarted.catalog = {x["model"]: set(EFFORTS) for x in DEFAULT_ROUTES.values()}
        self.assertEqual(restarted.thread_categories["t"]["task_floor"], "complex")
        restarted.threads["t"] = {**restarted.thread_categories["t"], "provider": "openai",
                                  "model": "gpt-5.6-luna", "effort": "low", "tier": "simple", "seen_turn": True}
        fake_jev.return_value = {"engine": "jev", "status": "ok", "continuity_strategy": "continue",
                                "route": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low"}}
        result = json.loads(restarted.client_line(encode(self.request("Sigue con lo que falta"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-sol", "high"))
        self.assertEqual(restarted.threads["t"]["engine_status"], "guardrail")
        history = (Path(self.tmp.name) / "state" / "history.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE_SENTINEL", history)

    def test_plan_does_not_clear_a_complex_task_floor(self):
        self.router.server_line(encode({"method": "item/completed", "params": {"threadId": "t", "item": {
            "type": "agentMessage", "text": "Quedan cambios pendientes y hay que ejecutar las pruebas."
        }}}))
        self.assertEqual(self.router.threads["t"]["task_floor"], "complex")
        self.router.server_line(encode({"method": "item/completed", "params": {"threadId": "t", "item": {
            "type": "agentMessage", "text": "Plan: primero preparo el siguiente paso y después revisamos el resultado."
        }}}))
        self.assertEqual(self.router.threads["t"]["task_floor"], "complex")
        restarted = Router(self.path, Path(self.tmp.name) / "state")
        self.assertEqual(restarted.thread_categories["t"]["task_floor"], "complex")

    def test_new_task_clears_persisted_capability_floor(self):
        self.router.threads["t"].update(task_floor="complex", tier="complex", seen_turn=True)
        self.router.client_line(encode(self.request("Nueva tarea: traduce hola al inglés")))
        self.assertNotIn("task_floor", self.router.threads["t"])
        restarted = Router(self.path, Path(self.tmp.name) / "state")
        self.assertNotIn("task_floor", restarted.thread_categories.get("t", {}))


if __name__ == "__main__":
    unittest.main()
