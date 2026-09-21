"""Native account smoke. Default reads version/catalog only. --live uses quota.

Live work is an ephemeral, isolated test session, never a saved user task. No
credentials or real conversations are read; MCP servers are disabled for it.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "dist" / "codex-router-v11.exe"


class Client:
    def __init__(self):
        self.p = subprocess.Popen([str(WRAPPER), "app-server"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.messages = queue.Queue()
        self.sequence = 0
        self.notifications = []
        self.tool_calls = 0
        self.stderr_bytes = 0
        self.native_models = []
        threading.Thread(target=self.read, daemon=True).start()
        threading.Thread(target=self.read_errors, daemon=True).start()

    def read(self):
        for line in self.p.stdout:
            self.messages.put(json.loads(line))
        self.messages.put(None)

    def read_errors(self):
        while block := self.p.stderr.read1(65536):
            self.stderr_bytes += len(block)  # Never print sensitive runtime logs.

    def send(self, message):
        self.p.stdin.write((json.dumps(message) + "\n").encode())
        self.p.stdin.flush()

    def next(self, timeout=45):
        message = self.messages.get(timeout=timeout)
        if message is None:
            raise RuntimeError("Bridge closed unexpectedly")
        if message.get("method") == "thread/settings/updated":
            settings = message.get("params", {}).get("threadSettings", {})
            self.native_models.append(settings.get("model"))
        if "id" in message and "method" in message:
            params = message.get("params") or {}
            if message["method"] == "item/tool/call" and params.get("tool") == "router_echo":
                assert params["arguments"] == {"value": 52}, "Tool arguments were changed"
                self.tool_calls += 1
                self.send({"id": message["id"], "result": {"success": True,
                    "contentItems": [{"type": "inputText", "text": "52"}]}})
            else:
                # Never approve unplanned filesystem, command or user-input requests.
                self.send({"id": message["id"], "error": {"code": -32601, "message": "Not allowed in smoke test"}})
        return message

    def call(self, method, params):
        self.sequence += 1
        rid = self.sequence
        self.send({"id": rid, "method": method, "params": params})
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            message = self.next(max(.1, deadline - time.monotonic()))
            if message.get("id") == rid and "method" not in message:
                if "error" in message:
                    raise RuntimeError(method + ": " + str(message["error"]))
                return message["result"]
            self.notifications.append(message)
        raise TimeoutError(method)

    def turn(self, thread, text):
        self.notifications.clear()
        result = self.call("turn/start", {"threadId": thread,
            "model": "gpt-6-astra", "effort": "high", "input": [{"type": "text", "text": text}],
            "collaborationMode": {"mode": "default", "settings": {
                "model": "gpt-6-astra", "reasoning_effort": "high", "developer_instructions": None}}})
        turn_id = result["turn"]["id"]
        output = ""
        deadline = time.monotonic() + 120
        buffered, self.notifications = self.notifications, []
        while time.monotonic() < deadline:
            message = buffered.pop(0) if buffered else self.next(max(.1, deadline - time.monotonic()))
            params = message.get("params") or {}
            if message.get("method") == "item/agentMessage/delta":
                output += params.get("delta", "")
            if message.get("method") == "turn/completed" and params.get("turn", {}).get("id") == turn_id:
                assert params["turn"]["status"] == "completed", params["turn"].get("error")
                return output
        raise TimeoutError("turn did not finish")

    def close(self):
        self.p.stdin.close()
        try:
            self.p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.p.terminate()  # Our isolated bridge only, never the user's app.
            self.p.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    version = subprocess.run([str(WRAPPER), "--version"],
        capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    assert version.returncode == 0 and b"codex-cli" in version.stdout
    report = {"version": version.stdout.decode().strip(), "live": args.live}
    client = Client()
    try:
        client.call("initialize", {"clientInfo": {"name": "personal_router_smoke", "version": "0.1.0"},
                                  "capabilities": {"experimentalApi": True}})
        client.send({"method": "initialized", "params": {}})
        models = client.call("model/list", {})
        report["models"] = [m["model"] for m in models["data"] if m["model"].startswith("gpt-")]
        (ROOT / "state" / "catalog.json").write_text(json.dumps({"checked": time.time(), "models": {
            m["model"]: [e["reasoningEffort"] for e in m.get("supportedReasoningEfforts", [])]
            for m in models["data"] if m["model"] in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-astra")
        }}, indent=2))
        account = client.call("account/read", {"refreshToken": False})
        report["account_type"] = (account.get("account") or {}).get("type")
        assert report["account_type"] == "chatgpt", "This test requires the existing ChatGPT subscription"
        print("Native handshake, model catalog and ChatGPT account: OK", flush=True)
        if args.live:
            overrides = {"features.shell_tool": False, "features.web_search": False,
                         "features.code_mode": False, "features.code_mode_host": False}
            # Read only server names; no credentials/values enter logs or reports.
            home_config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
            if home_config.exists():
                settings = tomllib.loads(home_config.read_text(encoding="utf-8-sig"))
                for name in settings.get("mcp_servers", {}):
                    overrides["mcp_servers." + name + ".enabled"] = False
            result = client.call("thread/start", {"ephemeral": True, "cwd": str(ROOT),
                "model": "gpt-6-astra", "modelProvider": "openai", "sandbox": "read-only",
                "approvalPolicy": "never", "config": overrides,
                "baseInstructions": "You are a minimal test assistant. Follow the requested output format. Use no tools except router_echo when asked. Do not access files, run commands, search or edit anything.",
                "developerInstructions": "This is an ephemeral routing smoke test, not project work.",
                "dynamicTools": [{"type": "function", "name": "router_echo", "description": "Return the supplied value unchanged.",
                    "inputSchema": {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"], "additionalProperties": False}}]})
            thread = result["thread"]["id"]
            first = client.turn(thread, "Traduce 'hola' al ingles. Responde solo con la palabra traducida. Recuerda que mi numero de prueba es 37.")
            assert first.strip().lower().strip(".!") in ("hello", "hi"), first
            print("Routed answer: OK", flush=True)
            second = client.turn(thread, "¿Que numero de prueba te di? Responde solo con ese numero.")
            assert second.strip().strip(".") == "37", second
            print("Conversation continuity: OK", flush=True)
            third = client.turn(thread, "Usa Luna. Llama a router_echo con value 52 y responde solo con el resultado. Es necesario llamar a la herramienta.")
            assert client.tool_calls == 1 and third.strip().strip(".") == "52", third
            print("Dynamic tool request and response: OK", flush=True)
            report["checks"] = ["real_answer", "context_preserved", "dynamic_tool_roundtrip"]
            report["test_thread_ephemeral"] = True
            assert "gpt-5.6-luna" in client.native_models, "No native model confirmation received"
            report["native_models"] = client.native_models
            print("Native engine confirms Luna and publishes its settings: OK", flush=True)
    finally:
        client.close()
    report["bridge_exit"] = client.p.returncode
    assert client.p.returncode == 0, "Bridge did not shut down cleanly"
    report["checked_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (ROOT / "state").mkdir(exist_ok=True)
    (ROOT / "state" / "smoke-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Clean shutdown: OK", flush=True)


if __name__ == "__main__":
    main()
