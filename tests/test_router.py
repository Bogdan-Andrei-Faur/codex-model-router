import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routing import DEFAULT_ROUTES, EFFORTS, classify, select_route
from router import Router


def encode(value):
    return (json.dumps(value, ensure_ascii=False) + "\n").encode()


class RoutingPolicyTests(unittest.TestCase):
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
        self.assertIn("Ultra no disponible", self.router.threads["t"]["reason"])

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
        self.router.server_line(encode({"method": "item/started", "params": {"threadId": "t", "item": {
            "type": "collabAgentToolCall", "senderThreadId": "t", "receiverThreadIds": ["child"],
            "model": "gpt-5.6-sol", "reasoningEffort": "high", "prompt": "SECRET_PROMPT",
            "agentsStates": {"child": {"status": "running", "message": "SECRET_RESULT"}}}}}))
        self.router.log({"event": "snapshot"})
        child = self.router.threads["child"]
        self.assertEqual((child["model"], child["parent"], child["confirmation"]), ("gpt-5.6-sol", "t", "Solicitado por agente"))
        logged = next((Path(self.tmp.name) / "state").glob("*.json")).read_text()
        self.assertNotIn("SECRET_", logged)


if __name__ == "__main__":
    unittest.main()
