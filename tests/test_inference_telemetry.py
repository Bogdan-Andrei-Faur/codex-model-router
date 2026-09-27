import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
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
            {"key": "conversation.id", "value": {"stringValue": "thread_12345678"}},
            {"key": "input_token_count", "value": {"intValue": "120"}},
            {"key": "output_token_count", "value": {"intValue": 8}},
            {"key": "cached_token_count", "value": {"intValue": "40"}},
            {"key": "reasoning_token_count", "value": {"intValue": "3"}},
            {"key": "duration_ms", "value": {"doubleValue": 812.5}},
            {"key": "ttft_ms", "value": {"doubleValue": 125.25}},
            {"key": "attempt", "value": {"intValue": "1"}},
            {"key": "http.response.status_code", "value": {"intValue": "200"}},
            {"key": "success", "value": {"boolValue": True}},
            {"key": "user.email", "value": {"stringValue": "private@example.invalid"}},
            {"key": "error.message", "value": {"stringValue": "PRIVATE_ERROR"}},
        ]}]}]}]}


class InferenceTelemetryTests(unittest.TestCase):
    def test_allowlist_drops_all_content_and_metadata(self):
        self.assertEqual(list(safe_records(payload())), [{"event_name": "codex.sse_event", "event_kind": "response.completed",
            "model": "gpt-5.6-terra", "effort": "medium", "thread_id": "thread_12345678",
            "inference_input_tokens": 120, "inference_output_tokens": 8, "inference_cached_tokens": 40,
            "inference_reasoning_tokens": 3, "inference_duration_ms": 812.5, "inference_ttft_ms": 125.25,
            "inference_attempt": 1, "inference_http_status": 200, "inference_success": True}])
        self.assertEqual(list(safe_records(payload(model="not-a-model"))), [])

    def test_loopback_receiver_emits_only_safe_record(self):
        events = []
        collector = LocalInferenceTelemetry(events.append)
        try:
            request = Request(collector.endpoint, data=json.dumps(payload()).encode(), method="POST",
                              headers={"Content-Type": "application/json", "Authorization": "Bearer " + collector.token})
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(events, [{"event_name": "codex.sse_event", "event_kind": "response.completed",
                "model": "gpt-5.6-terra", "effort": "medium", "thread_id": "thread_12345678",
                "inference_input_tokens": 120, "inference_output_tokens": 8, "inference_cached_tokens": 40,
                "inference_reasoning_tokens": 3, "inference_duration_ms": 812.5, "inference_ttft_ms": 125.25,
                "inference_attempt": 1, "inference_http_status": 200, "inference_success": True}])
            self.assertNotIn("PRIVATE_PROMPT", repr(events))
            self.assertNotIn("private@example.invalid", repr(events))
            self.assertNotIn("PRIVATE_ERROR", repr(events))
            expected = {"enabled": True, "requests": 1, "records_scanned": 1,
                                                     "eligible_records": 1, "events_without_model": 0,
                                                     "unrecognized_records": 0, "invalid_requests": 0,
                                                     "invalid_size": 0, "invalid_encoding": 0, "invalid_payload": 0,
                                                     "invalid_io": 0, "unauthorized_requests": 0, "unexpected_path": 0,
                                                     "rejected_connections": 0,
                                                     "completion_records": 1, "failure_records": 0,
                                                     "api_request_records": 0, "stream_records": 1}
            self.assertEqual({key:collector.snapshot()[key] for key in expected}, expected)
        finally:
            collector.close()

    def test_router_attributes_only_one_matching_live_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); config = root / "config.json"
            config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}), encoding="utf-8")
            router = Router(config, root / "state")
            router.threads["one"] = {"decision_id": "d1", "status": "inProgress", "phase_status": "active",
                "phase_model": "gpt-5.6-terra", "phase_effort": "medium", "phase_pipeline": [], "turn_id": "turn-one"}
            router.current_decisions["one"] = "d1"
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium",
                                      "thread_id": "one", "turn_id": "turn-one",
                                      "inference_input_tokens": 120, "inference_duration_ms": 812.5})
            self.assertEqual(router.threads["one"]["observed_model"], "gpt-5.6-terra")
            self.assertEqual(router.stats["telemetry_confirmed"], 1)
            history = [json.loads(line) for line in (root / "state" / "history.jsonl").read_text().splitlines()]
            self.assertEqual((history[-1]["inference_input_tokens"], history[-1]["inference_duration_ms"]),
                             (120, 812.5))
            router.threads["one"].update(phase_status="completed", completed_at=time.time())
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium", "thread_id": "one", "turn_id": "turn-one"})
            self.assertEqual(router.stats["telemetry_confirmed"], 2)
            router.threads["two"] = dict(router.threads["one"], decision_id="d2")
            router.observe_inference({"event_kind": "response.completed", "model": "gpt-5.6-terra", "effort": "medium"})
            self.assertEqual(router.stats["telemetry_unattributed"], 1)

    def test_bounded_metrics_reject_invalid_or_excessive_values(self):
        sample = payload()
        attributes = sample["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["attributes"]
        attributes.extend([
            {"key": "tool_token_count", "value": {"intValue": "-1"}},
            {"key": "cache_write_token_count", "value": {"intValue": "1000000001"}},
            {"key": "duration_ms", "value": {"doubleValue": "nan"}},
            {"key": "http.response.status_code", "value": {"intValue": "999"}},
        ])
        record = list(safe_records(sample))[0]
        self.assertNotIn("inference_tool_tokens", record)
        self.assertNotIn("inference_cache_write_tokens", record)
        self.assertNotEqual(record.get("inference_http_status"), 999)

    def test_receiver_counts_safe_rejection_causes(self):
        collector = LocalInferenceTelemetry(lambda _: None)
        try:
            for headers in ({"Authorization": "Bearer wrong"}, {"Authorization": "Bearer " + collector.token, "Content-Encoding": "br"}):
                request = Request(collector.endpoint, data=b"{}", method="POST", headers=headers)
                with self.assertRaises(HTTPError):
                    urlopen(request, timeout=3)
            health = collector.snapshot()
            self.assertEqual(health["unauthorized_requests"], 1)
            self.assertEqual(health["invalid_encoding"], 1)
            self.assertEqual(health["invalid_requests"], 1)
        finally:
            collector.close()
