import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase_control import TOOL, SPEC
from routing import DEFAULT_ROUTES, EFFORTS
from router import Router
from task_modes import mode_path
from state_store import atomic_json


def wire(value):
    return (json.dumps(value) + "\n").encode()


class PhaseControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"
        self.settings = {"enabled": True, "phase_routing": True, "sync_picker": False,
                         "routes": copy.deepcopy(DEFAULT_ROUTES)}
        self.config.write_text(json.dumps(self.settings))
        self.router = Router(self.config, self.root / "state")
        self.router.client_line(wire({"id": 0, "method": "initialize", "params": {
            "capabilities": {"experimentalApi": True}}}))
        self.router.catalog = {r["model"]: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        self.enroll()
        self.begin()

    def enroll(self):
        request = {"id": 1, "method": "thread/start", "params": {"modelProvider": "openai",
                   "dynamicTools": [{"type": "function", "name": "existing", "inputSchema": {}}]}}
        sent = json.loads(self.router.client_line(wire(request)))
        self.assertEqual(sent["params"]["dynamicTools"][:-1], request["params"]["dynamicTools"])
        self.assertEqual(sent["params"]["dynamicTools"][-1], SPEC)
        self.router.server_line(wire({"id": 1, "result": {"thread": {"id": "t"},
                                 "modelProvider": "openai", "model": "gpt-5.6-terra"}}))

    def begin(self, source="automatic", floor=None, model="gpt-5.6-terra"):
        row = self.router.threads["t"]
        row.update(provider="openai", model=model, accepted_model=model,
                   effort="medium", accepted_effort="medium", turn_id="turn")
        self.router.phases.begin("t", "turn", {"source": source, "quality_floor": floor})

    def checkpoint(self, **overrides):
        params = {"threadId": "t", "turnId": "turn", "tool": TOOL, "namespace": None,
                  "arguments": {"phase": "implement", "complexity": "complex"}}
        params.update(overrides)
        return self.router.server_line(wire({"id": "call", "method": "item/tool/call", "params": params}))

    def status(self, value):
        return json.loads(value["result"]["contentItems"][0]["text"])["status"]

    def test_tool_is_held_until_native_ack_and_other_requests_pass(self):
        self.assertFalse(self.checkpoint())
        request, = self.router.drain_outbound()
        self.assertEqual(request["method"], "turn/settings/update")
        self.assertEqual(request["params"]["model"], "gpt-5.6-sol")
        self.assertEqual(self.router.threads["t"]["accepted_model"], "gpt-5.6-terra")
        other = wire({"id": "other", "method": "account/read", "params": {}})
        self.assertEqual(self.router.client_line(other), other)
        self.assertFalse(self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}})))
        reply, = self.router.drain_outbound()
        self.assertEqual((reply["id"], self.status(reply)), ("call", "applied"))
        self.assertEqual(self.router.threads["t"]["accepted_model"], "gpt-5.6-sol")
        self.assertNotIn("observed_model", self.router.threads["t"])

    def test_rejection_disables_further_updates(self):
        self.checkpoint()
        request, = self.router.drain_outbound()
        self.router.server_line(wire({"id": request["id"], "error": {"code": -32600}}))
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "rejected")
        self.checkpoint(arguments={"phase": "verify", "complexity": "complex"})
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")

    def test_timeout_is_uncertain_and_late_reply_is_swallowed(self):
        now = [0]
        self.router.phases.clock = lambda: now[0]
        self.checkpoint()
        request, = self.router.drain_outbound()
        now[0] = 11
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "unknown_after_timeout")
        self.assertFalse(self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}})))
        self.assertEqual(self.router.drain_outbound(), [])
        self.assertEqual(self.router.threads["t"]["accepted_model"], "gpt-5.6-terra")

    def test_completed_turn_cleans_pending_call_and_ignores_late_ack(self):
        self.checkpoint()
        request, = self.router.drain_outbound()
        self.router.server_line(wire({"method": "turn/completed", "params": {
            "threadId": "t", "turn": {"id": "turn", "status": "interrupted"}}}))
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "cancelled")
        self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}}))
        self.assertEqual(self.router.drain_outbound(), [])
        self.assertNotIn("t", self.router.phases.turns)

    def test_control_messages_disable_new_phase_changes(self):
        for method in ("turn/interrupt", "turn/steer", "thread/settings/update", "turn/settings/update"):
            with self.subTest(method=method):
                self.begin()
                raw = wire({"id": 8, "method": method, "params": {"threadId": "t"}})
                self.assertEqual(self.router.client_line(raw), raw)
                self.checkpoint()
                self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")

    def test_manual_explicit_preserved_and_paused_never_switch(self):
        for source in ("manual", "explicit", "preserved", "agent"):
            self.begin(source)
            self.checkpoint()
            self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")
        self.begin()
        atomic_json(mode_path(self.router.state_dir, "t"), {"thread": "t", "mode": "manual"})
        self.checkpoint()
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")

    def test_quality_floor_is_not_lowered_by_agent(self):
        self.begin(floor="complex")
        self.checkpoint(arguments={"phase": "summarize", "complexity": "simple"})
        self.assertEqual(self.router.drain_outbound()[0]["params"]["model"], "gpt-5.6-sol")

    def test_astra_boundary_unknown_models_and_missing_catalog_preserve(self):
        for model in ("gpt-6-astra", "unknown"):
            self.begin(model=model)
            self.checkpoint()
            self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")
        self.begin()
        self.router.catalog = {}
        self.checkpoint()
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")

    def test_duplicate_phase_is_bounded(self):
        self.checkpoint()
        request, = self.router.drain_outbound()
        self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}}))
        self.router.drain_outbound()
        self.checkpoint()
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "checkpoint_limit")

    def test_later_critical_work_reports_new_turn_requirement(self):
        self.checkpoint(arguments={"phase": "verify", "complexity": "critical"})
        reply, = self.router.drain_outbound()
        self.assertEqual(self.status(reply), "requires_new_turn")
        self.assertIn("Stop this phase", reply["result"]["contentItems"][0]["text"])

    def test_late_ack_does_not_revive_completed_task(self):
        self.checkpoint()
        request, = self.router.drain_outbound()
        self.router.server_line(wire({"method": "thread/closed", "params": {"threadId": "t"}}))
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "cancelled")
        self.assertFalse(self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}})))
        self.assertEqual(self.router.drain_outbound(), [])

    def test_pending_control_does_not_release_tool_before_ack(self):
        self.checkpoint()
        request, = self.router.drain_outbound()
        self.router.client_line(wire({"id": 99, "method": "turn/interrupt", "params": {"threadId": "t"}}))
        self.assertEqual(self.router.drain_outbound(), [])
        self.router.server_line(wire({"id": request["id"], "result": {"status": "applied"}}))
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "applied")

    def test_no_experimental_handshake_means_no_registration(self):
        self.router.phases.api_enabled = False
        raw = wire({"id": 12, "method": "thread/start", "params": {}})
        self.assertEqual(self.router.client_line(raw), raw)

    def test_foreign_tool_requests_are_forwarded_exactly(self):
        self.assertTrue(self.checkpoint(threadId="foreign"))
        self.assertTrue(self.checkpoint(namespace="foreign"))
        self.assertTrue(self.checkpoint(tool="existing"))
        self.assertEqual(self.router.drain_outbound(), [])

    def test_child_inheriting_owned_tool_keeps_its_native_configuration(self):
        self.router.threads["child"] = {"parent": "t", "model": "gpt-6-astra"}
        self.assertFalse(self.checkpoint(threadId="child"))
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")
        self.assertEqual(self.router.threads["child"]["model"], "gpt-6-astra")

    def test_malformed_checkpoint_replies_without_exposing_arguments(self):
        self.checkpoint(arguments={"phase": "secret raw payload"})
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "invalid_checkpoint")
        for path in self.router.state_dir.rglob("*.json*"):
            self.assertNotIn("secret raw payload", path.read_text())

    def test_restart_can_handle_owned_tool_when_disabled(self):
        self.settings["phase_routing"] = False
        self.config.write_text(json.dumps(self.settings))
        self.router = Router(self.config, self.root / "state")
        self.assertFalse(self.checkpoint())
        self.assertEqual(self.status(self.router.drain_outbound()[0]), "preserved")

    def test_no_injection_into_internal_or_foreign_or_colliding_tasks(self):
        for params in ({"ephemeral": True}, {"modelProvider": "ollama"}, {"dynamicTools": [SPEC]}):
            raw = wire({"id": 9, "method": "thread/start", "params": params})
            self.assertEqual(self.router.client_line(raw), raw)
        self.settings["phase_routing"] = False
        self.config.write_text(json.dumps(self.settings))
        raw = wire({"id": 9, "method": "thread/start", "params": {}})
        self.assertEqual(self.router.client_line(raw), raw)

    def test_turn_start_ack_uses_the_actual_routing_decision(self):
        self.router.phases.turns.clear()
        raw = wire({"id": 77, "method": "turn/start", "params": {"threadId": "t",
            "model": "gpt-5.6-terra", "input": [{"type": "text", "text": "Investiga una condición de carrera entre dos procesos."}]}})
        self.router.client_line(raw)
        self.router.server_line(wire({"id": 77, "result": {"turn": {"id": "new-turn"}}}))
        self.assertTrue(self.router.phases.turns["t"]["allowed"])
        self.assertEqual(self.router.phases.turns["t"]["id"], "new-turn")
        self.assertEqual(self.router.phases.turns["t"]["floor"], "complex")


if __name__ == "__main__":
    unittest.main()
