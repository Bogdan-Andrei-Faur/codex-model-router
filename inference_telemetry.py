"""Loopback-only inference evidence for the local Codex bridge.

The collector deliberately discards raw OTel payloads. It retains only an
allowlist sufficient to establish model/effort evidence and never persists
prompts, resources, URLs, tool calls, identities, headers or response text.
"""
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra"))
EFFORTS = frozenset(("low", "medium", "high", "xhigh", "max", "ultra"))
EVENT_NAMES = frozenset(("codex.api_request", "codex.sse_event", "codex.websocket_event"))
EVENT_KINDS = frozenset(("response.created", "response.completed", "response.failed"))
MAX_BYTES = 512 * 1024


def safe_records(payload, health=None):
    """Extract a tiny, content-free set of OTel log fields."""
    for resource in payload.get("resourceLogs", []):
        for scope in resource.get("scopeLogs", []):
            for log in scope.get("logRecords", []):
                if health is not None:
                    health["records_scanned"] += 1
                record = {}
                for attribute in log.get("attributes", []):
                    key = attribute.get("key")
                    value = attribute.get("value", {}).get("stringValue")
                    if key in ("model", "slug", "gen_ai.request.model", "gen_ai.response.model") and value in MODELS:
                        record["model"] = value
                    elif key in ("model_reasoning_effort", "reasoning_effort") and value in EFFORTS:
                        record["effort"] = value
                    elif key == "event.name" and value in EVENT_NAMES:
                        record["event_name"] = value
                    elif key == "event.kind" and value in EVENT_KINDS:
                        record["event_kind"] = value
                if record.get("event_name") and record.get("model"):
                    if health is not None:
                        health["eligible_records"] += 1
                    yield record
                elif health is not None and record.get("event_name"):
                    health["events_without_model"] += 1
                elif health is not None:
                    health["unrecognized_records"] += 1


class LocalInferenceTelemetry:
    """A short-lived HTTP collector bound only to the loopback interface."""
    def __init__(self, receive):
        self.receive = receive
        self.lock = threading.Lock()
        self.health = {"enabled": True, "requests": 0, "records_scanned": 0,
                       "eligible_records": 0, "events_without_model": 0,
                       "unrecognized_records": 0, "invalid_requests": 0,
                       "unexpected_path": 0}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    if self.path != "/v1/logs":
                        with owner.lock:
                            owner.health["unexpected_path"] += 1
                        self.send_response(404)
                        self.end_headers()
                        return
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= MAX_BYTES:
                        raise ValueError("invalid payload size")
                    raw = self.rfile.read(size)
                    if self.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    with owner.lock:
                        health = owner.health
                        health["requests"] += 1
                        records = list(safe_records(json.loads(raw), health))
                    for record in records:
                        owner.receive(record)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"{}")
                except (ValueError, TypeError, json.JSONDecodeError, OSError, EOFError):
                    with owner.lock:
                        owner.health["invalid_requests"] += 1
                    self.send_response(400)
                    self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    @property
    def endpoint(self):
        return "http://127.0.0.1:%d/v1/logs" % self.server.server_port

    def snapshot(self):
        """Return counters only; payloads and values are never retained."""
        with self.lock:
            return dict(self.health)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)
