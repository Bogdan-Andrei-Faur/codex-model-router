import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routing import DEFAULT_ROUTES, EFFORTS, classify, classify_agent_identity, select_route, select_route_details
from decision_engines import inline_images
from router import Router


def encode(value):
    return (json.dumps(value, ensure_ascii=False) + "\n").encode()


class RoutingPolicyTests(unittest.TestCase):
    def test_only_inline_image_data_is_eligible_for_opt_in_ollama_vision(self):
        items = [{"type": "localImage", "path": r"C:\\private\\capture.png"},
                 {"type": "image", "url": "data:image/png;base64,c2FmZQ=="},
                 {"type": "image", "url": "https://example.com/image.png"}]
        self.assertEqual(inline_images(items), ["c2FmZQ=="])

    def test_spanish_and_english_workloads(self):
        cases = [
            ("Traduce al ingles: Nos vemos mañana.", "simple"),
            ("Explica que hace esta funcion.", "simple"),
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

    def test_ambiguous_followups_keep_context(self):
        for prompt in ("Sí, hazlo", "Continúa", "¿Por qué ocurre?", "Ahora compruébalo"):
            self.assertEqual(classify(prompt, "critical").tier, "critical")
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
        self.assertEqual(classify("Continúa", "critical", previous_effort="max").effort, "max")
        self.assertEqual(classify("Crea un formulario", "simple").tier, "normal")
        self.assertEqual(classify("Sigue fallando", "critical", previous_effort="xhigh").effort, "max")

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

    @patch("router.run_provider")
    def test_provider_failure_falls_back_to_rules(self, fake_provider):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "provider"}))
        fake_provider.return_value = {"engine": "provider", "status": "unavailable", "latency_ms": 10,
                                      "engine_model": "Ollama · glm-5.3-flash:cloud"}
        result = json.loads(self.router.client_line(encode(self.request("Traduce hola al inglés"))))
        self.assertEqual((result["params"]["model"], result["params"]["effort"]), ("gpt-5.6-luna", "low"))
        self.assertIn("no estuvo disponible", self.router.threads["t"]["model_reason"])

    @patch("router.run_provider")
    def test_invalid_provider_choice_is_not_presented_as_a_connection_failure(self, provider):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES, "routing_engine": "provider"}))
        provider.return_value = {"engine": "provider", "status": "invalid", "latency_ms": 2200}
        result = json.loads(self.router.client_line(encode(self.request("Traduce hola al inglés"))))
        self.assertEqual(result["params"]["model"], "gpt-5.6-luna")
        self.assertIn("respondió sin una elección única válida", self.router.threads["t"]["model_reason"])
        self.assertNotIn("no estuvo disponible", self.router.threads["t"]["model_reason"])
        self.assertIn("respaldo local:", self.router.threads["t"]["effort_reason"])

    @patch("router.run_provider")
    def test_rules_comparison_records_baseline_without_changing_provider_choice(self, provider):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES,
            "routing_engine": "provider", "comparison_engines": ["rules", "rules", "provider"]}))
        provider.return_value = {"engine": "provider", "status": "ok", "route": {
            "model": "gpt-5.6-terra", "effort": "medium", "tier": "normal"}}
        result = json.loads(self.router.client_line(encode(self.request("Traduce hola al inglés"))))
        self.assertEqual(result["params"]["model"], "gpt-5.6-terra")
        records = [json.loads(line) for line in (Path(self.tmp.name) / "state" / "history.jsonl").read_text().splitlines()]
        comparisons = [item for item in records if item["event"] == "engine_comparison"]
        self.assertEqual([(item["routing_engine"], item["engine_active"]) for item in comparisons],
                         [("provider", True), ("rules", False)])
        self.assertEqual(comparisons[1]["proposed_model"], "gpt-5.6-luna")
        provider.assert_called_once()

    @patch("router.run_provider")
    def test_comparison_aliases_do_not_duplicate_calls_or_replace_local_reasons(self, provider):
        self.path.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES,
            "routing_engine": "rules", "comparison_engines": ["rules", "ollama", "provider"]}))
        provider.return_value = {"engine": "provider", "status": "ok", "route": {
            "model": "gpt-5.6-terra", "effort": "medium", "tier": "normal"}}
        result = json.loads(self.router.client_line(encode(self.request("Traduce hola al inglés"))))
        self.assertEqual(result["params"]["model"], "gpt-5.6-luna")
        self.assertNotIn("Proveedor", self.router.threads["t"]["model_reason"])
        self.assertEqual(self.router.threads["t"]["routing_engine"], "rules")
        provider.assert_called_once()

    def test_non_turn_messages_are_byte_identical(self):
        for data in [b'  {"id":9, "method":"turn/interrupt", "params":{"threadId":"t","turnId":"q"}} \n',
                     b'{"id":7,"result":{"decision":"approved"}}\n', b'not json\n', b'[1,2]\n']:
            self.assertEqual(self.router.client_line(data), data)

    def test_active_turn_is_not_replayed_or_rerouted(self):
        self.router.server_line(encode({"method": "turn/started", "params": {"threadId": "t"}}))
        raw = encode(self.request())
        self.assertEqual(self.router.client_line(raw), raw)

    def test_pending_turn_does_not_reroute_a_second_message(self):
        self.router.client_line(encode(self.request()))
        raw = encode(self.request("Nueva tarea: investiga una migración"))
        self.assertEqual(self.router.client_line(raw), raw)

    def test_unknown_provider_or_model_is_preserved(self):
        for provider, model in [("ollama", "gemma4:26b"), (None, "gpt-6-astra"), ("openai", "future-new-model")]:
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

    def test_reopened_conversation_retains_high_tier_for_short_followup(self):
        self.router.client_line(encode({"id": 3, "method": "thread/resume", "params": {"threadId": "t"}}))
        self.router.threads.clear()
        self.router.server_line(encode({"id": 3, "result": {"thread": {"id": "t"},
            "modelProvider": "openai", "model": "gpt-6-astra"}}))
        result = json.loads(self.router.client_line(encode(self.request("Continúa"))))
        self.assertEqual(result["params"]["model"], "gpt-6-astra")

    def test_logs_contain_no_prompt_attachment_or_auth(self):
        self.router.client_line(encode(self.request("Traduce PRIVATE_SENTINEL password sk-not-real")))
        text = "".join(p.read_text() for p in (Path(self.tmp.name) / "state").glob("*.json"))
        self.assertNotIn("PRIVATE_SENTINEL", text)
        self.assertNotIn("sk-not-real", text)
        self.assertIn("gpt-5.6-luna", text)

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
                         ["decision_created", "engine_comparison", "decision_accepted", "decision_completed"])
        self.assertEqual(len({r["decision_id"] for r in records}), 1)
        self.assertEqual(records[0]["source"], "automatic")
        self.assertIn("model_reason", records[0])
        self.assertIn("effort_reason", records[0])
        self.assertEqual(records[0]["agent_category"], "text")
        self.assertEqual(records[0]["agent_confidence"], "media")
        self.assertEqual(records[1]["routing_engine"], "rules")
        self.assertEqual(records[1]["proposed_model"], "gpt-5.6-luna")
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
        self.assertNotEqual(self.router.threads["t"].get("confirmation"), "Aceptado por Codex")
        self.router.server_line(encode({"id": 7, "result": {"turn": {"id": "q"}}}))
        self.router.server_line(encode({"method": "thread/settings/updated", "params": {"threadId": "t", "threadSettings": {"model": "gpt-6-astra", "effort": "max"}}}))
        self.assertEqual(self.router.threads["t"]["model"], "gpt-5.6-luna")
        self.assertEqual(self.router.threads["t"]["effort"], "low")
        self.assertEqual(self.router.threads["t"]["confirmation"], "Aceptado por Codex")
        self.assertEqual(self.router.stats, {"accepted": 1, "non_astra": 1})
        self.router.server_line(encode({"method": "turn/completed", "params": {"threadId": "t", "turn": {"status": "completed"}}}))
        self.assertEqual(self.router.threads["t"]["status"], "completed")

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


if __name__ == "__main__":
    unittest.main()
