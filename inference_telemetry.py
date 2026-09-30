"""Loopback-only inference evidence for the local Codex bridge.

The collector deliberately discards raw OTel payloads. It retains only a typed,
bounded allowlist sufficient to establish model/effort evidence and measure
inference cost/latency. It never persists prompts, resources, URLs, tool calls,
identities, headers, free-form errors or response text.
"""
import gzip
import io
import hmac
import math
import secrets
import hashlib
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import zlib

from model_catalog import MODELS as REVIEWED_MODELS
MODELS = frozenset(REVIEWED_MODELS)
EFFORTS = frozenset(("low", "medium", "high", "xhigh", "max", "ultra"))
EVENT_NAMES = frozenset(("codex.api_request", "codex.sse_event", "codex.websocket_event"))
EVENT_KINDS = frozenset(("response.created", "response.completed", "response.failed"))
MAX_WIRE_BYTES = 4 * 1024 * 1024
MAX_DECODED_BYTES = 16 * 1024 * 1024
# Fixed bins are counters, not samples of private payloads. The last decoded
# bin is only a lower bound: decompression stops at MAX_DECODED_BYTES + 1.
SIZE_BINS = ((512 * 1024, "512k"), (1024 * 1024, "1m"),
             (4 * 1024 * 1024, "4m"), (16 * 1024 * 1024, "16m"))
RECORD_COUNTERS = ("records_scanned", "eligible_records", "events_without_model",
                   "unrecognized_records", "completion_records", "failure_records",
                   "api_request_records", "stream_records")
MAX_CONNECTIONS = 8
CONNECTION_TIMEOUT = 2
PROCESSING_WAIT_TIMEOUT = CONNECTION_TIMEOUT / 2

COUNT_FIELDS = {
    "input_token_count": "inference_input_tokens",
    "output_token_count": "inference_output_tokens",
    "cached_token_count": "inference_cached_tokens",
    "cache_write_token_count": "inference_cache_write_tokens",
    "reasoning_token_count": "inference_reasoning_tokens",
    "tool_token_count": "inference_tool_tokens",
}
MILLISECOND_FIELDS = {"duration_ms": "inference_duration_ms", "ttft_ms": "inference_ttft_ms"}


def attribute_value(value):
    if not isinstance(value, dict):
        return None
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in value:
            return value[key]


def bounded_number(value, maximum, integer=False):
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0 or number > maximum:
        return None
    return number


class BoundedServer(ThreadingHTTPServer):
    """Admit work before creating a thread, with a total connection deadline."""
    daemon_threads = True
    # The kernel accept queue must absorb a short burst so process_request can
    # reject work above MAX_CONNECTIONS with a bounded close instead of making
    # local clients time out before admission control runs.
    request_queue_size = MAX_CONNECTIONS * 2

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            if hasattr(self, 'rejected'):
                self.rejected()
            self.shutdown_request(request)
            return
        request.settimeout(CONNECTION_TIMEOUT)
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        timer = threading.Timer(CONNECTION_TIMEOUT, self.shutdown_request, args=(request,))
        timer.daemon = True
        try:
            timer.start()
            super().process_request_thread(request, address)
        finally:
            timer.cancel()
            self.shutdown_request(request)
            self.slots.release()


def safe_records(payload, health=None):
    """Extract content-free identity and performance fields from OTel logs."""
    for resource in payload.get("resourceLogs", []):
        for scope in resource.get("scopeLogs", []):
            for log in scope.get("logRecords", []):
                if health is not None:
                    health["records_scanned"] += 1
                record = {}
                for attribute in log.get("attributes", []):
                    key = attribute.get("key")
                    value = attribute_value(attribute.get("value"))
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
                    elif key in COUNT_FIELDS:
                        number = bounded_number(value, 1_000_000_000, integer=True)
                        if number is not None:
                            record[COUNT_FIELDS[key]] = number
                    elif key in MILLISECOND_FIELDS:
                        number = bounded_number(value, 86_400_000)
                        if number is not None:
                            record[MILLISECOND_FIELDS[key]] = number
                    elif key == "attempt":
                        number = bounded_number(value, 100, integer=True)
                        if number is not None:
                            record["inference_attempt"] = number
                    elif key == "http.response.status_code":
                        number = bounded_number(value, 599, integer=True)
                        if number is not None and number >= 100:
                            record["inference_http_status"] = number
                    elif key == "success" and type(value) is bool:
                        record["inference_success"] = value
                stamp = log.get("timeUnixNano")
                if stamp and str(stamp).isdigit():
                    record["timestamp"] = int(stamp) / 1e9
                if record.get("response_id") or stamp:
                    identity = (record.get("thread_id"), record.get("turn_id"), record.get("response_id"), stamp, record.get("event_kind"), record.get("model"))
                    record["event_id"] = hashlib.sha256(repr(identity).encode()).hexdigest()
                if record.get("event_name") and record.get("model"):
                    if health is not None:
                        health["eligible_records"] += 1
                        if record.get("event_name") == "codex.api_request":
                            health["api_request_records"] += 1
                        else:
                            health["stream_records"] += 1
                        if record.get("event_kind") == "response.completed":
                            health["completion_records"] += 1
                        elif record.get("event_kind") == "response.failed":
                            health["failure_records"] += 1
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
        # At most eight bounded wire bodies, but only one expanded JSON batch
        # in memory at a time. Callbacks never hold this lock or the health lock.
        self.parse_lock = threading.Lock()
        self.health = {"enabled": True, "requests": 0, "records_scanned": 0,
                       "eligible_records": 0, "events_without_model": 0,
                       "unrecognized_records": 0, "invalid_requests": 0,
                       "invalid_size": 0, "invalid_encoding": 0,
                       "invalid_wire_size": 0, "invalid_decoded_size": 0,
                       "invalid_length": 0, "processing_busy": 0,
                       "invalid_payload": 0, "invalid_io": 0,
                       "unauthorized_requests": 0, "unexpected_path": 0,
                       "rejected_connections": 0,
                       "completion_records": 0, "failure_records": 0,
                       "api_request_records": 0, "stream_records": 0}
        for stage in ("wire", "decoded"):
            for label in [item[1] for item in SIZE_BINS] + ["over16m"]:
                self.health["size_" + stage + "_" + label] = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, body=b""):
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()

            def do_POST(self):
                try:
                    authorization = self.headers.get("Authorization", "")
                    if not hmac.compare_digest(authorization, "Bearer " + owner.token):
                        with owner.lock:
                            owner.health["unauthorized_requests"] += 1
                        self.respond(401)
                        # Drain only a bounded declared body, without decoding.
                        # Closing a Windows socket with unread bytes can reset
                        # it before the peer receives the rejection status.
                        size = int(self.headers.get("Content-Length", "0"))
                        if 0 < size <= MAX_WIRE_BYTES:
                            self.rfile.read(size)
                        return
                    if self.path != "/v1/logs":
                        with owner.lock:
                            owner.health["unexpected_path"] += 1
                        self.respond(404)
                        return
                    lengths = self.headers.get_all("Content-Length", [])
                    if (len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,20}", lengths[0])
                            or self.headers.get("Transfer-Encoding")):
                        raise ValueError("length")
                    size = int(lengths[0])
                    if size <= 0:
                        raise ValueError("length")
                    owner.record_size("wire", size)
                    if size > MAX_WIRE_BYTES:
                        raise ValueError("wire_size")
                    raw = self.rfile.read(size)
                    if len(raw) != size:
                        raise ValueError("io")
                    if not owner.parse_lock.acquire(timeout=PROCESSING_WAIT_TIMEOUT):
                        raise ValueError("busy")
                    try:
                        encoding = self.headers.get("Content-Encoding", "identity").lower().strip()
                        if encoding == "gzip":
                            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                                raw = stream.read(MAX_DECODED_BYTES + 1)
                        elif encoding != "identity":
                            raise ValueError("encoding")
                        owner.record_size("decoded", len(raw))
                        if len(raw) > MAX_DECODED_BYTES:
                            raise ValueError("decoded_size")
                        delta = dict.fromkeys(RECORD_COUNTERS, 0)
                        records = list(safe_records(json.loads(raw), delta))
                    finally:
                        raw = b""
                        owner.parse_lock.release()
                    with owner.lock:
                        owner.health["requests"] += 1
                        for key, value in delta.items():
                            owner.health[key] += value
                    for record in records:
                        owner.receive(record)
                    self.respond(200, b"{}")
                except (ValueError, TypeError, AttributeError, RecursionError, OSError, EOFError, zlib.error) as error:
                    reason = str(error)
                    status = 400
                    with owner.lock:
                        owner.health["invalid_requests"] += 1
                        if isinstance(error, OSError) or str(error) == "io":
                            owner.health["invalid_io"] += 1
                        elif reason in ("wire_size", "decoded_size"):
                            owner.health["invalid_size"] += 1
                            owner.health["invalid_" + reason] += 1
                            status = 413
                        elif reason == "length":
                            owner.health["invalid_length"] += 1
                        elif reason == "busy":
                            owner.health["processing_busy"] += 1
                            status = 503
                        elif str(error) == "encoding":
                            owner.health["invalid_encoding"] += 1
                        else:
                            owner.health["invalid_payload"] += 1
                    try:
                        self.respond(status)
                    except OSError:
                        pass

        self.server = BoundedServer(("127.0.0.1", 0), Handler)
        def rejected():
            with self.lock:
                self.health['rejected_connections'] += 1
        self.server.rejected = rejected
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    @property
    def endpoint(self):
        return "http://127.0.0.1:%d/v1/logs" % self.server.server_port

    def record_size(self, stage, size):
        label = next((label for limit, label in SIZE_BINS if size <= limit), "over16m")
        with self.lock:
            self.health["size_" + stage + "_" + label] += 1

    def snapshot(self):
        """Return counters only; payloads and values are never retained."""
        with self.lock:
            return dict(self.health)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)
