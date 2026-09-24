import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inference_telemetry import LocalInferenceTelemetry, safe_records
from router import Router
from routing import DEFAULT_ROUTES


def payload(model="gpt-5.6-terra", effort="medium", kind="response.completed"):
    return {"resourceLogs": [{"resource": {"attributes": [{"key": "secret", "value": {"stringValue": "never-keep"}}]},
        "scopeLogs": [{"logRecords": [{"body": {"stringValue": "PRIVATE_PROMPT"}, "attributes": [
            {"key": "event.name", "value": {"stringValue": "codex.sse_event"}},
            {"key": "event.kind", "value": {"stringValue": kind}},
            {"key": "model", "value": {"stringValue": model}},
            {"key": "model_reasoning_effort", "value": {"stringValue": effort}},
        ]}]}]}]}


class InferenceTelemetryTests(unittest.TestCase):
    def test_allowlist_drops_all_content_and_metadata(self):
        self.assertEqual(list(safe_records(payload())), [{"event_name": "codex.sse_event", "event_kind": "response.completed",
                                                           "model": "gpt-5.6-terra", "effort": "medium"}])
        self.assertEqual(list(safe_records(payload(model="not-a-model"))), [])

    def test_loopback_receiver_emits_only_safe_record(self):
        events = []
        collector = LocalInferenceTelemetry(events.append)
        try:
            request = Request(collector.endpoint, data=json.dumps(payload()).encode(), method="POST",
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(events, [{"event_name": "codex.sse_event", "event_kind": "response.completed",
                                       "model": "gpt-5.6-terra", "effort": "medium"}])
            self.assertNotIn("PRIVATE_PROMPT", repr(events))
        finally:
            collector.close()

    def test_router_attributes_only_one_matching_live_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = root / "config.json"
            config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}), encoding="utf-8")
            router = Router(config, root / "state")
            router.threads["one"] = {"decision_id": "d1", "status": "inProgress", "phase_status": "active",
                "phase_model": "gpt-5.6-terra", "phase_effort": "medium", "phase_pipeline": []}
            router.current_decisions["one"] = "d1"
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium"})
            self.assertEqual(router.threads["one"]["observed_model"], "gpt-5.6-terra")
            self.assertEqual(router.stats["telemetry_confirmed"], 1)
            router.threads["one"].update(phase_status="completed", updated=time.time())
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium"})
            self.assertEqual(router.stats["telemetry_confirmed"], 2)
            router.threads["two"] = dict(router.threads["one"], decision_id="d2")
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium"})
            self.assertEqual(router.stats["telemetry_unattributed"], 1)
