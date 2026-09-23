"""Opt-in subscription probe: phase boundaries, never active user tasks.

Uses an ephemeral native thread, a temporary empty working directory and one
in-memory echo tool. Does not connect to Desktop, route user work or deploy.
Run with --live. Output records protocol evidence, not prompts or credentials.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import tomllib
import secrets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_runtime import discover
from smoke_native import Client, ROOT


class PhaseClient(Client):
    def __init__(self, command):
        self.events = []
        self.turn_id = None
        self.switch_result = None
        self.effort_result = None
        self.receipt = secrets.token_hex(6)
        super().__init__(command)

    def next(self, timeout=45):
        event = self.messages.get(timeout=timeout)
        if event is None:
            raise RuntimeError("Native connection closed")
        self.events.append(event)
        params = event.get("params") or {}
        if event.get("method") == "turn/started":
            self.turn_id = params["turn"]["id"]
        if "id" in event and "method" in event:
            if event["method"] == "item/tool/call" and params.get("tool") == "router_echo":
                assert params["arguments"] == {"value": 52}
                self.tool_calls += 1
                assert self.tool_calls == 1, "Synthetic tool was repeated"
                self.effort_result = self.call("turn/settings/update", {
                    "threadId": params["threadId"], "turnId": self.turn_id,
                    "effort": "high"})
                assert self.effort_result == {"status": "applied"}
                try:
                    self.switch_result = self.call("turn/settings/update", {
                        "threadId": params["threadId"], "turnId": self.turn_id,
                        "model": "gpt-6-astra", "effort": "medium"})
                except RuntimeError as error:
                    # Rejected model transitions are a probe result, not a reason
                    # to change approval policy or interrupt/replay work.
                    self.switch_result = {"status": "rejected", "reason": str(error)}
                self.send({"id": event["id"], "result": {"success": True,
                    "contentItems": [{"type": "inputText", "text": self.receipt}]}})
            else:
                self.send({"id": event["id"], "error": {"code": -32601, "message": "Not allowed in isolated probe"}})
        return event

    def phase(self, thread, text, model, effort):
        self.notifications.clear()
        self.switch_result = None
        self.effort_result = None
        start = time.monotonic()
        begin = len(self.events)
        result = self.call("turn/start", {"threadId": thread, "model": model,
            "effort": effort, "input": [{"type": "text", "text": text}],
            "collaborationMode": {"mode": "default", "settings": {
                "model": model, "reasoning_effort": effort, "developer_instructions": None}}})
        turn_id = result["turn"]["id"]
        output = ""
        deadline = time.monotonic() + 100
        buffered, self.notifications = self.notifications, []
        while time.monotonic() < deadline:
            event = buffered.pop(0) if buffered else self.next(max(.1, deadline-time.monotonic()))
            params = event.get("params") or {}
            if event.get("method") == "item/agentMessage/delta":
                output += params.get("delta", "")
            if event.get("method") == "turn/completed" and params.get("turn", {}).get("id") == turn_id:
                assert params["turn"]["status"] == "completed", "Phase did not complete"
                reroutes = [e for e in self.events[begin:] if e.get("method") == "model/rerouted"]
                assert not reroutes, "Native backend rerouted the requested model"
                return output, {"model_requested": model, "effort_requested": effort,
                    "turn_id": turn_id, "status": "completed", "seconds": round(time.monotonic()-start, 2),
                    "live_switch_ack": self.switch_result,
                    "live_effort_ack": self.effort_result,
                    "inference_model_independently_verified": False}
        raise TimeoutError("Phase exceeded 100 seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live to authorize two short model turns on the existing subscription")
    install = discover()
    overrides = {"features.shell_tool": False, "features.web_search": False,
        "features.code_mode": True, "features.code_mode_host": True, "features.apps": False,
        "features.multi_agent": False, "features.step_model_switching": True}
    config = Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex")))/"config.toml"
    if config.exists():
        for name in tomllib.loads(config.read_text(encoding="utf-8-sig")).get("mcp_servers", {}):
            overrides["mcp_servers."+name+".enabled"] = False
    command = [str(install.backend)]
    for key, value in overrides.items():
        command += ["-c", key+"="+json.dumps(value)]
    command += ["app-server"]
    client = PhaseClient(command)
    scratch = tempfile.TemporaryDirectory(prefix="codex-phase-probe-", ignore_cleanup_errors=True)
    report = {"desktop_version": install.version, "ephemeral": True, "phases": [],
        "scope": "native protocol only; Desktop presentation and approvals unverified"}
    try:
        client.call("initialize", {"clientInfo": {"name": "personal_phase_probe", "version": "0.1.0"},
            "capabilities": {"experimentalApi": True}})
        client.send({"method": "initialized", "params": {}})
        assert (client.call("account/read", {"refreshToken": False}).get("account") or {}).get("type") == "chatgpt"
        with scratch as cwd:
            created = client.call("thread/start", {"ephemeral": True, "cwd": cwd,
                "model": "gpt-5.6-terra", "modelProvider": "openai", "sandbox": "read-only",
                "approvalPolicy": "never", "config": overrides,
                "baseInstructions": "Isolated continuity test. Use only router_echo when requested, via code mode if required. In code mode print the returned value with text(await tools.router_echo({value:52})); do not discard the returned value. No files, shell, network or other tools. Reply exactly as asked.",
                "developerInstructions": "Synthetic probe. Never execute project work.",
                "dynamicTools": [{"type": "function", "name": "router_echo", "description": "Return an unpredictable receipt for the supplied integer. You must call this tool to learn the receipt.",
                    "inputSchema": {"type": "object", "properties": {"value": {"type": "integer"}},
                        "required": ["value"], "additionalProperties": False}}]})
            tid = created["thread"]["id"]
            output, record = client.phase(tid, "Remember checkpoint CODE-37. Call router_echo once with value 52 to obtain its unpredictable receipt. You cannot infer the receipt. Then respond exactly with the checkpoint followed by a space and the receipt returned by the tool.", "gpt-5.6-terra", "medium")
            report["phases"].append(record)
            assert output.strip().strip(".") == "CODE-37 " + client.receipt and client.tool_calls == 1, "Live-switch turn failed: " + repr((output[:200], client.tool_calls, client.switch_result, [e for e in client.events if e.get('method') in ('warning','configWarning')]))
            print("Single turn complete; effort update: applied; model update: " + client.switch_result["status"], flush=True)
            output, record = client.phase(tid, "Continue from the completed phase. Do not call tools. Return exactly the checkpoint followed by a space and the previous tool result.", "gpt-6-astra", "medium")
            assert output.strip().strip(".") == "CODE-37 " + client.receipt, "Context was not retained"
            assert client.tool_calls == 1, "Tool repeated after handoff"
            report["phases"].append(record)
            report.update(context_preserved=True, tool_not_repeated=True,
                distinct_native_turns=report["phases"][0]["turn_id"] != record["turn_id"])
            print("Phase 2 complete: Astra, medium; context retained, tool not repeated", flush=True)
            unavailable = client.call("turn/settings/update", {"threadId": tid, "turnId": record["turn_id"],
                "model": "gpt-5.6-terra", "effort": "low"})
            assert unavailable == {"status": "targetUnavailable"}
            report["completed_turn_update"] = unavailable["status"]
            client.close()  # Release the cwd before the temporary directory is cleaned up.
    finally:
        if client.p.poll() is None:
            client.close()
        scratch.cleanup()
        report["bridge_exit"] = client.p.returncode
        report["checked_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (ROOT/"state"/"phase-probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert report["bridge_exit"] == 0, "Native process did not close cleanly"
    print("Clean shutdown; report in state/phase-probe.json", flush=True)


if __name__ == "__main__":
    main()
