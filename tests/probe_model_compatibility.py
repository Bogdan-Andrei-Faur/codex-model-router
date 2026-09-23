"""Opt-in model-transition probe on an isolated native subscription session.

No production settings are changed. A loopback-only OTLP collector retains only
an allowlist of model/effort/event fields; it never persists raw telemetry.
"""
import argparse
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_runtime import discover
from smoke_native import Client, ROOT

MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra")
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
FINAL_TARGET = dict(zip(MODELS, (MODELS[1], MODELS[2], MODELS[0], MODELS[3])))


class Collector:
    def __init__(self):
        self.events = []
        self.requests = 0
        self.errors = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 8 * 1024 * 1024:
                        raise ValueError("Invalid telemetry size")
                    raw = self.rfile.read(size)
                    if self.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    owner.consume(json.loads(raw))
                    owner.requests += 1
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"{}")
                except Exception:
                    owner.errors += 1
                    self.send_response(400)
                    self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def consume(self, payload):
        # Ignore resources, identities, prompts, tool output, URLs and log bodies.
        for resource in payload.get("resourceLogs", []):
            for scope in resource.get("scopeLogs", []):
                for log in scope.get("logRecords", []):
                    record = {}
                    for attribute in log.get("attributes", []):
                        key = attribute.get("key")
                        value = attribute.get("value", {}).get("stringValue")
                        if key in ("model", "slug", "gen_ai.request.model", "gen_ai.response.model") and value in MODELS:
                            record[key] = value
                        elif key in ("model_reasoning_effort", "reasoning_effort") and value in EFFORTS:
                            record[key] = value
                        elif key == "event.name" and value in ("codex.api_request", "codex.sse_event", "codex.websocket_event", "codex.conversation_starts"):
                            record[key] = value
                        elif key == "event.kind" and value in ("response.created", "response.completed", "response.failed"):
                            record[key] = value
                    if record.get("event.name") and (record.get("model") or record.get("slug")):
                        record["time_unix_nano"] = str(log.get("timeUnixNano") if log.get("timeUnixNano") not in (None, "0", 0) else log.get("observedTimeUnixNano", "0"))
                        self.events.append(record)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)


class MatrixClient(Client):
    def __init__(self, command, source, final_target):
        self.source = source
        self.final_target = final_target
        self.turn_id = None
        self.receipt = secrets.token_hex(8)
        self.transitions = []
        self.events = []
        super().__init__(command)

    def change(self, thread, model, effort="medium"):
        try:
            return self.call("turn/settings/update", {
                "threadId": thread, "turnId": self.turn_id, "model": model, "effort": effort})
        except RuntimeError as error:
            return {"status": "rejected", "reason": str(error)}

    def next(self, timeout=45):
        event = self.messages.get(timeout=timeout)
        if event is None:
            raise RuntimeError("Isolated native process closed")
        self.events.append(event)
        params = event.get("params") or {}
        if event.get("method") == "turn/started":
            self.turn_id = params["turn"]["id"]
        if "id" in event and "method" in event:
            if event["method"] == "item/tool/call" and params.get("tool") == "router_echo":
                assert params["arguments"] == {"value": 52}
                self.tool_calls += 1
                assert self.tool_calls == 1, "Receipt tool repeated"
                tid = params["threadId"]
                for target in MODELS:
                    if target == self.source:
                        continue
                    result = self.change(tid, target)
                    self.transitions.append({"from": self.source, "to": target, **result})
                    print(self.source + " -> " + target + ": " + result["status"], flush=True)
                    if result.get("status") == "applied":
                        assert self.change(tid, self.source) == {"status": "applied"}, "Could not restore baseline"
                target = self.final_target
                self.final_switch = {"model": target, "effort": "high", **self.change(tid, target, "high")}
                assert self.final_switch["status"] == "applied", "Final test transition rejected"
                self.send({"id": event["id"], "result": {"success": True,
                    "contentItems": [{"type": "inputText", "text": self.receipt}]}})
            else:
                self.send({"id": event["id"], "error": {"code": -32601, "message": "Not allowed in isolated probe"}})
        return event

    def run_turn(self, thread):
        self.notifications.clear()
        result = self.call("turn/start", {"threadId": thread, "model": self.source, "effort": "medium",
            "input": [{"type": "text", "text": "Remember checkpoint MATRIX-52. Call router_echo once with value 52 to obtain its unpredictable receipt. Then respond exactly with the checkpoint followed by a space and the receipt. You cannot infer this receipt."}],
            "collaborationMode": {"mode": "default", "settings": {
                "model": self.source, "reasoning_effort": "medium", "developer_instructions": None}}})
        self.turn_id = result["turn"]["id"]
        buffered, self.notifications = self.notifications, []
        output = ""
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            event = buffered.pop(0) if buffered else self.next(max(.1, deadline-time.monotonic()))
            params = event.get("params") or {}
            if event.get("method") == "item/agentMessage/delta":
                output += params.get("delta", "")
            if event.get("method") == "turn/completed" and params.get("turn", {}).get("id") == self.turn_id:
                assert params["turn"]["status"] == "completed", "Turn failed"
                assert output.strip().strip(".") == "MATRIX-52 " + self.receipt, "Receipt/context not preserved"
                assert self.tool_calls == 1, "Synthetic tool missing or repeated"
                assert not any(e.get("method") == "model/rerouted" for e in self.events), "Unexpected native reroute"
                return
        raise TimeoutError("Compatibility turn exceeded deadline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--reverse", action="store_true", help="Verify the other three compatible directions")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required: four synthetic turns consume subscription quota")
    install = discover()
    overrides = {"features.shell_tool": False, "features.web_search": False,
        "features.code_mode": True, "features.code_mode_host": True, "features.apps": False,
        "features.multi_agent": False, "features.step_model_switching": True,
        "otel.log_user_prompt": False, "otel.trace_exporter": "none", "otel.metrics_exporter": "none"}
    config = Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex")))/"config.toml"
    if config.exists():
        for name in tomllib.loads(config.read_text(encoding="utf-8-sig")).get("mcp_servers", {}):
            overrides["mcp_servers."+name+".enabled"] = False
    report = {"desktop_version": install.version,
        "backend_version": subprocess.check_output([str(install.backend), "--version"], text=True).strip(),
        "scope": "isolated ephemeral threads; synthetic tool; no Desktop orchestration or child agents", "runs": []}
    try:
        sources = MODELS[:3] if args.reverse else MODELS
        targets = dict(zip(MODELS[:3], (MODELS[2], MODELS[0], MODELS[1]))) if args.reverse else FINAL_TARGET
        for source in sources:
            collector = Collector()
            client = None
            scratch = tempfile.TemporaryDirectory(prefix="codex-model-matrix-", ignore_cleanup_errors=True)
            row = {"source": source, "status": "incomplete"}
            report["runs"].append(row)
            try:
                command = [str(install.backend)]
                for key, value in overrides.items():
                    command += ["-c", key + "=" + json.dumps(value)]
                endpoint = "http://127.0.0.1:" + str(collector.server.server_port) + "/v1/logs"
                command += ["-c", 'otel.exporter={otlp-http={endpoint="' + endpoint + '",protocol="json"}}', "app-server"]
                client = MatrixClient(command, source, targets[source])
                client.call("initialize", {"clientInfo": {"name": "model_compatibility_probe", "version": "0.1.0"},
                    "capabilities": {"experimentalApi": True}})
                client.send({"method": "initialized", "params": {}})
                assert (client.call("account/read", {"refreshToken": False}).get("account") or {}).get("type") == "chatgpt"
                created = client.call("thread/start", {"ephemeral": True, "cwd": scratch.name,
                    "model": source, "modelProvider": "openai", "sandbox": "read-only", "approvalPolicy": "never",
                    "baseInstructions": "Isolated continuity test. Use only router_echo via code mode when requested. Print its result with text(await tools.router_echo({value:52})); never discard it. No files, shell, network or other tools. Reply exactly as asked.",
                    "developerInstructions": "Synthetic probe. Never execute project work.",
                    "dynamicTools": [{"type": "function", "name": "router_echo", "description": "Return an unpredictable receipt for the supplied integer. Call this tool to learn the receipt.",
                        "inputSchema": {"type": "object", "properties": {"value": {"type": "integer"}},
                            "required": ["value"], "additionalProperties": False}}]})
                started = time.monotonic()
                client.run_turn(created["thread"]["id"])
                row.update(status="completed", seconds=round(time.monotonic()-started, 2),
                    context_preserved=True, tool_calls=client.tool_calls, final_switch=client.final_switch)
            finally:
                if client:
                    client.close()
                    row.update(transitions=client.transitions, native_exit=client.p.returncode)
                collector.close()
                scratch.cleanup()
                row.update(telemetry_requests=collector.requests, telemetry_errors=collector.errors,
                    telemetry=sorted(collector.events, key=lambda e: int(e.get("time_unix_nano") or 0)))
                completed = [event for event in row["telemetry"]
                    if event.get("event.name") == "codex.sse_event" and event.get("event.kind") == "response.completed"]
                row["native_telemetry_transition_verified"] = (
                    any(e.get("model") == source and e.get("model_reasoning_effort") == "medium" for e in completed)
                    and any(e.get("model") == targets[source] and e.get("model_reasoning_effort") == "high" for e in completed))
                row["server_model_identity_independently_attested"] = False
                print(source + ": " + row["status"] + "; telemetry events " + str(len(collector.events)), flush=True)
    finally:
        report["checked_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        filename = "model-compatibility-reverse-probe.json" if args.reverse else "model-compatibility-probe.json"
        (ROOT/"state"/filename).write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert all(r.get("native_exit") == 0 for r in report["runs"]), "Native shutdown failed"
    assert all(r.get("native_telemetry_transition_verified") for r in report["runs"]), "Model/effort telemetry missing"
    print("Report: state/" + filename, flush=True)


if __name__ == "__main__":
    main()
