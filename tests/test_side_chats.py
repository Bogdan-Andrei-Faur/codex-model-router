"""Replay Desktop side-chat protocol; no network or real conversations."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from router import Router
from routing import DEFAULT_ROUTES, EFFORTS


def wire(message):
    return (json.dumps(message) + "\n").encode()


class SideChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}))
        self.router = Router(self.config, self.root / "state")
        self.router.catalog = {r["model"]: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
        self.router.threads["parent"] = {"provider": "openai", "model": "gpt-6-astra",
                                         "task_floor": "critical", "status": "inProgress"}

    def tearDown(self):
        self.tmp.cleanup()

    def fork(self, source="user", order="before", ephemeral=True, provider="openai"):
        params = {"threadId": "parent", "ephemeral": ephemeral, "excludeTurns": True,
                  "threadSource": source, "developerInstructions": "PRIVATE_INSTRUCTIONS"}
        request = wire({"id": 1, "method": "thread/fork", "params": params})
        self.assertEqual(self.router.client_line(request), request)
        thread = {"id": "side", "ephemeral": ephemeral, "forkedFromId": "parent",
                  "name": "PRIVATE_TITLE", "status": {"type": "idle"}}
        notice = wire({"method": "thread/started", "params": {"thread": thread}})
        if order == "before":
            self.router.server_line(notice)
        self.router.server_line(wire({"id": 1, "result": {"thread": thread,
            "model": "gpt-6-astra", "modelProvider": provider, "reasoningEffort": "high"}}))
        if order == "after":
            self.router.server_line(notice)

    def turn(self):
        return {"id": 2, "method": "turn/start", "params": {
            "threadId": "side", "model": "gpt-6-astra", "effort": "high",
            "input": [{"type": "text", "text": "Traduce hola al inglés: PRIVATE_PROMPT"}],
            "permissions": ":read-only", "approvalPolicy": "never",
            "collaborationMode": {"mode": "default", "settings": {
                "model": "gpt-6-astra", "reasoning_effort": "high", "developer_instructions": "KEEP"}}}}

    def start_turn(self):
        output = self.router.client_line(wire(self.turn()))
        self.router.server_line(wire({"id": 2, "result": {"turn": {"id": "turn-side"}}}))
        self.router.server_line(wire({"method": "turn/started", "params": {
            "threadId": "side", "turn": {"id": "turn-side"}}}))
        return output

    def test_user_fork_routes_in_both_notification_orders_without_mutating_parent(self):
        for order in ("before", "after"):
            with self.subTest(order=order):
                self.router = Router(self.config, self.root / order)
                self.router.catalog = {r["model"]: set(EFFORTS) for r in DEFAULT_ROUTES.values()}
                self.router.threads["parent"] = {"model": "gpt-6-astra", "task_floor": "critical"}
                parent = copy.deepcopy(self.router.threads["parent"])
                self.fork(order=order)
                original = self.turn()
                routed = json.loads(self.start_turn())
                self.assertEqual(routed["params"]["model"], "gpt-6-luna")
                self.assertEqual(self.router.threads["parent"], parent)
                self.assertFalse(self.router.threads["side"].get("parent"))
                self.assertEqual(self.router.threads["side"]["forked_from"], "parent")
                expected = copy.deepcopy(original)
                expected["params"].update(model="gpt-6-luna", effort="low")
                expected["params"]["collaborationMode"]["settings"].update(
                    model="gpt-6-luna", reasoning_effort="low")
                self.assertEqual(routed, expected)

    def test_internal_and_unknown_forks_keep_native_model_even_with_ancestry(self):
        for source in ("title_generation", "mcp_extension_host", None):
            with self.subTest(source=source):
                self.fork(source=source)
                with patch.object(self.router, "route_turn") as route:
                    raw = wire(self.turn())
                    self.assertEqual(self.router.client_line(raw), raw)
                    route.assert_not_called()
                self.assertEqual(self.router.events[-1]["reason"], "internal_ephemeral")
                self.assertNotIn("side", self.router.inventory.visible(self.router.threads))

    def test_side_chat_uses_jev_when_selected(self):
        self.config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES,
                                          "routing_engine": "jev"}))
        self.fork()
        with patch("router.run_jev", return_value={"status": "ok", "engine": "jev",
                   "route": {"model": "gpt-6-luna", "effort": "low", "tier": "simple"},
                   "continuity_strategy": "reassess"}) as classify:
            self.start_turn()
            classify.assert_called_once()

    def test_temporary_chat_visible_only_while_active_and_never_saved(self):
        self.fork()
        self.start_turn()
        self.router.inventory.catalog = {"parent": {}}
        self.router.inventory.catalog_observed = {"parent", "side"}
        self.router.server_line(wire({"method": "thread/name/updated", "params": {
            "threadId": "side", "threadName": "PRIVATE_RENAMED_TITLE"}}))
        self.router.server_line(wire({"method": "item/completed", "params": {
            "threadId": "side", "item": {"type": "agentMessage", "text":
            "Plan: implementar autenticación y validar todos los permisos. PRIVATE_RESPONSE"}}}))
        visible = self.router.inventory.visible(self.router.threads)
        self.assertEqual(visible["side"]["name"], "Chat lateral")
        self.router.log({"event": "test"})
        self.assertFalse((self.router.state_dir / "history.jsonl").exists())
        self.assertFalse((self.router.state_dir / "workloads").exists())
        for path in self.router.state_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn("PRIVATE_", path.read_text(encoding="utf-8"))
        self.router.server_line(wire({"method": "turn/completed", "params": {
            "threadId": "side", "turn": {"id": "turn-side", "status": "completed"}}}))
        self.assertNotIn("side", self.router.inventory.visible(self.router.threads))
        restarted = Router(self.config, self.router.state_dir)
        self.assertNotIn("side", restarted.thread_categories)
        # A late classifier callback also stays out of permanent history.
        self.router.record_history("engine_comparison", thread="side", title="PRIVATE_LATE")
        self.assertFalse((self.router.state_dir / "history.jsonl").exists())

    def test_sparse_read_and_notification_preserve_side_identity(self):
        self.fork()
        self.router.client_line(wire({"id": 3, "method": "thread/read", "params": {"threadId": "side"}}))
        self.router.server_line(wire({"id": 3, "result": {"thread": {"id": "side"}}}))
        self.router.server_line(wire({"method": "thread/started", "params": {"thread": {"id": "side"}}}))
        self.assertTrue(self.router.threads["side"]["side_chat"])
        self.assertTrue(self.router.threads["side"]["ephemeral"])

    def test_persistent_fork_still_saves_decisions(self):
        self.fork(ephemeral=False)
        self.start_turn()
        self.assertFalse(self.router.threads["side"]["side_chat"])
        self.assertTrue((self.router.state_dir / "history.jsonl").exists())

    def test_manual_pause_and_other_provider_are_respected(self):
        self.fork()
        raw = wire(self.turn())
        self.assertEqual(self.router.client_line(raw, mode_at_submission="manual"), raw)
        self.router.pending.clear()
        self.config.write_text(json.dumps({"enabled": False, "routes": DEFAULT_ROUTES}))
        self.assertEqual(self.router.client_line(raw), raw)
        self.router.pending.clear()
        self.config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}))
        self.router.threads["side"]["provider"] = "other"
        self.assertEqual(self.router.client_line(raw), raw)

    def test_closing_active_side_chat_does_not_leave_a_ghost_agent(self):
        self.fork()
        self.start_turn()
        self.router.server_line(wire({"method": "thread/closed", "params": {"threadId": "side"}}))
        self.assertNotIn("side", self.router.active)
        self.assertNotIn("side", self.router.pending)
        self.assertNotIn("side", self.router.inventory.visible(self.router.threads))
        self.assertNotIn("PRIVATE_", json.dumps(self.router.threads["side"]))
        self.assertEqual(self.router.threads["parent"]["status"], "inProgress")
        self.router.server_line(wire({"method": "thread/status/changed", "params": {
            "threadId": "side", "status": {"type": "active"}}}))
        self.assertNotIn("side", self.router.inventory.visible(self.router.threads))
        self.assertFalse((self.router.state_dir / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
