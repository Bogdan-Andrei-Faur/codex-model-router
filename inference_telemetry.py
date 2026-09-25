"""Loopback-only inference evidence for the local Codex bridge.

The collector deliberately discards raw OTel payloads. It retains only an
allowlist sufficient to establish model/effort evidence and never persists
prompts, resources, URLs, tool calls, identities, headers or response text.
"""
import gzip
import io
import hmac
import secrets
import hashlib
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra"))
EFFORTS = frozenset(("low", "medium", "high", "xhigh", "max", "ultra"))
EVENT_NAMES = frozenset(("codex.api_request", "codex.sse_event", "codex.websocket_event"))
EVENT_KINDS = frozenset(("response.created", "response.completed", "response.failed"))
MAX_BYTES = 512 * 1024
MAX_CONNECTIONS = 8
READ_TIMEOUT = 2


class BoundedServer(ThreadingHTTPServer):
    """Admit work before creating a thread, with a total connection deadline."""
    daemon_threads = True

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        request.settimeout(READ_TIMEOUT)
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        timer = threading.Timer(READ_TIMEOUT, self.shutdown_request, args=(request,))
        timer.daemon = True
        try:
            timer.start()
            super().process_request_thread(request, address)
        finally:
            timer.cancel()
            self.shutdown_request(request)
            self.slots.release()


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
                    elif key in ("conversation.id", "thread.id", "thread_id", "turn.id", "turn_id", "response.id", "response_id") and isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{8,160}", value):
                        field = "thread_id" if key in ("conversation.id", "thread.id", "thread_id") else "turn_id" if key.startswith("turn") else "response_id"
                        record[field] = value
                stamp = log.get("timeUnixNano")
                if stamp and str(stamp).isdigit():
                    record["timestamp"] = int(stamp) / 1e9
                if record.get("response_id") or stamp:
                    identity = (record.get("thread_id"), record.get("turn_id"), record.get("response_id"), stamp, record.get("event_kind"), record.get("model"))
                    record["event_id"] = hashlib.sha256(repr(identity).encode()).hexdigest()
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
        self.token = secrets.token_hex(32)
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
                    authorization = self.headers.get("Authorization", "")
                    if not hmac.compare_digest(authorization, "Bearer " + owner.token):
                        self.send_response(401)
                        self.send_header("Content-Length", "0")
                        self.send_header("Connection", "close")
                        self.end_headers()
                        self.wfile.flush()
                        # Drain only a bounded declared body, without decoding.
                        # Closing a Windows socket with unread bytes can reset
                        # it before the peer receives the rejection status.
                        size = int(self.headers.get("Content-Length", "0"))
                        if 0 < size <= MAX_BYTES:
                            self.rfile.read(size)
                        return
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
                    if len(raw) != size:
                        raise ValueError("truncated payload")
                    if self.headers.get("Content-Encoding") == "gzip":
                        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                            raw = stream.read(MAX_BYTES + 1)
                        if len(raw) > MAX_BYTES:
                            raise ValueError("expanded payload too large")
                    elif self.headers.get("Content-Encoding", "identity") != "identity":
                        raise ValueError("unsupported encoding")
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
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError, OSError, EOFError):
                    with owner.lock:
                        owner.health["invalid_requests"] += 1
                    try:
                        self.send_response(400)
                        self.end_headers()
                    except OSError:
                        pass

        self.server = BoundedServer(("127.0.0.1", 0), Handler)
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
