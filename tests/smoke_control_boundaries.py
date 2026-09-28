"""Opt-in native approval, rejection and cancellation probe.

Runs three short isolated subscription turns through the current router source.
The approval case writes one temporary marker in ignored router state after an
explicit native approval callback, then removes it.  The cancellation case
interrupts a sleep command and verifies the turn ends as interrupted.  No
Desktop conversation, configuration, credential, or tracked project file is
read or changed.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_runtime import discover
from platform_support import with_loopback_telemetry
from probe_model_compatibility import Collector
from routing import DEFAULT_ROUTES
from smoke_native import Client, ROOT
from control_contract import exact_approval_command, approval_command
from control_runtime import process_alive, process_state, safe_process_topology, sleep_command, read_process_marker


class ControlClient(Client):
    def __init__(self, command, scratch, marker, config):
        self.scratch = str(Path(scratch).resolve())
        self.marker = str(Path(marker).resolve())
        self.mode = None
        self.approvals = []
        self.cancel_request_id = None
        self.cancel_response = None
        self.work_started = False
        self.cancelled_item_type = None
        self.methods = []
        self.process_marker = Path(scratch) / 'running.json'
        self.running_pids = []
        self.command_metadata = []
        self.command_topology = []
        super().__init__(command, {"PERSONAL_CODEX_ROUTER_CONFIG": str(config)})

    def next(self, timeout=45):
        message = self.messages.get(timeout=timeout)
        if message is None:
            raise RuntimeError("Native connection closed")
        params = message.get("params") or {}
        if "method" in message:
            self.methods.append(message["method"])
        if message.get("id") == self.cancel_request_id and "method" not in message:
            self.cancel_response = message
        if "id" in message and "method" in message:
            method = message["method"]
            if method == "item/commandExecution/requestApproval" and self.mode in ("approval", "rejection"):
                command = params.get("command") or ""
                cwd = str(params.get("cwd") or "")
                assert exact_approval_command(command, self.marker), "Unexpected command approval"
                assert str(Path(cwd).resolve()) == self.scratch, "Approval escaped the temporary directory"
                decision = "accept" if self.mode == "approval" else "decline"
                self.approvals.append({"method": method, "decision": decision})
                self.send({"id": message["id"], "result": {"decision": decision}})
            else:
                self.send({"id": message["id"], "error": {
                    "code": -32601, "message": "Not allowed in isolated control probe"}})
        if message.get("method") == "item/started" and self.mode == "cancellation":
            item = params.get("item") or {}
            item_type = item.get("type")
            if item_type == "commandExecution" and self.cancel_request_id is None:
                self.command_metadata.append({
                    "parameter_keys": sorted(params),
                    "item_keys": sorted(item),
                    "process_id": item.get("processId"),
                    "process_id_type": type(item.get("processId")).__name__,
                })
                self.running_pids = read_process_marker(self.process_marker)
                assert len(self.running_pids) == 2 and all(type(pid) is int and pid > 1 for pid in self.running_pids)
                assert all(process_alive(pid) for pid in self.running_pids), "Expected live parent and child"
                self.command_topology = safe_process_topology(self.running_pids)
                self.work_started = True
                self.cancelled_item_type = item_type
                self.sequence += 1
                self.cancel_request_id = self.sequence
                self.send({"id": self.cancel_request_id, "method": "turn/interrupt", "params": {
                    "threadId": params["threadId"], "turnId": params["turnId"]}})
        return message

    def run_turn(self, thread, prompt, mode, timeout=120):
        self.mode = mode
        self.notifications.clear()
        result = self.call("turn/start", {"threadId": thread,
            "model": "gpt-5.6-terra", "effort": "medium",
            "input": [{"type": "text", "text": prompt}],
            "collaborationMode": {"mode": "default", "settings": {
                "model": "gpt-5.6-terra", "reasoning_effort": "medium",
                "developer_instructions": None}}})
        turn_id = result["turn"]["id"]
        output = ""
        deadline = time.monotonic() + timeout
        buffered, self.notifications = self.notifications, []
        while time.monotonic() < deadline:
            message = buffered.pop(0) if buffered else self.next(max(.1, deadline - time.monotonic()))
            params = message.get("params") or {}
            if message.get("method") == "item/agentMessage/delta":
                output += params.get("delta", "")
            if message.get("method") == "turn/completed" and params.get("turn", {}).get("id") == turn_id:
                return output, params["turn"]["status"]
        raise TimeoutError(mode + " turn did not finish")


def disabled_integrations():
    overrides = {"features.web_search": False, "features.apps": False,
        "features.multi_agent": False, "features.code_mode": True,
        "features.code_mode_host": True, "features.shell_tool": True}
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if config.exists():
        for name in tomllib.loads(config.read_text(encoding="utf-8-sig")).get("mcp_servers", {}):
            overrides["mcp_servers." + name + ".enabled"] = False
    return overrides


def command_for(overrides, endpoint, token):
    install = discover()
    command = [sys.executable, str(ROOT / "router.py")]
    for key, value in overrides.items():
        command += ["-c", key + "=" + json.dumps(value)]
    return install, command[:2] + with_loopback_telemetry(
        command[2:] + ["app-server"], endpoint, token)


def start_thread(client, cwd, overrides, approval_policy, instructions, sandbox="read-only"):
    result = client.call("thread/start", {"ephemeral": True, "cwd": cwd,
        "model": "gpt-5.6-terra", "modelProvider": "openai", "sandbox": sandbox,
        "approvalPolicy": approval_policy, "config": overrides,
        "baseInstructions": instructions,
        "developerInstructions": "Isolated native control-boundary probe; never perform project work."})
    return result["thread"]["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--native", action="store_true", help="Compare directly with the installed backend, bypassing the router")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required: this uses three isolated subscription turns")
    overrides = disabled_integrations()
    collector = Collector()
    endpoint = "http://127.0.0.1:" + str(collector.server.server_port) + "/v1/logs"
    install, command = command_for(overrides, endpoint, collector.token)
    if args.native:
        command = [str(install.backend), *command[2:]]
    with tempfile.TemporaryDirectory(prefix="router-control-probe-") as scratch:
        config = Path(scratch) / "config.json"
        config.write_text(json.dumps({"installation_mode": "auto", "enabled": True,
            "phase_routing": True, "sync_picker": False, "inference_telemetry": False,
            "prompt_logging": False, "routing_engine": "rules", "comparison_engines": [],
            "routes": DEFAULT_ROUTES}), encoding="utf-8")
        outside = tempfile.TemporaryDirectory(prefix="router-approval-marker-", dir=ROOT / "state")
        marker = Path(outside.name) / "control-boundary-marker"
        client = ControlClient(command, scratch, marker, config)
        report = {"desktop_version": install.version, "ephemeral": True,
            "router_present": not args.native,
            "scope": "isolated native approval and cancellation callbacks", "passed": False}
        try:
            client.call("initialize", {"clientInfo": {
                "name": "personal_control_boundary_probe", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True}})
            client.send({"method": "initialized", "params": {}})
            assert (client.call("account/read", {"refreshToken": False}).get("account") or {}).get("type") == "chatgpt"

            approval_thread = start_thread(client, scratch, overrides, "on-request",
                "Use the shell tool once with the exact command: " + approval_command(str(marker)) + " . "
                "If the sandbox rejects it, repeat the exact command with sandbox_permissions "
                "require_escalated and the justification 'Synthetic approval probe'. "
                "Do not use other tools or paths. After it succeeds, reply exactly APPROVAL-COMPLETE.")
            output, status = client.run_turn(approval_thread,
                "Run the prescribed command now. It must be executed, not described.", "approval")
            assert status == "completed", status
            assert client.approvals == [{"method": "item/commandExecution/requestApproval", "decision": "accept"}], {
                "approvals": client.approvals, "marker_exists": marker.exists(),
                "status": status, "methods": sorted(set(client.methods))}
            assert marker.read_text(encoding="utf-8") == "APPROVED"
            assert "APPROVAL-COMPLETE" in output
            report["approval"] = {"request_observed": True, "decision": "accept",
                "command_completed": True, "turn_status": status}

            marker.unlink()
            denial_thread = start_thread(client, scratch, overrides, "on-request",
                "Use the shell tool with exactly: " + approval_command(str(marker)) +
                " . Request escalation if the sandbox rejects it. If approval is declined, stop immediately and reply DENIED. Do not retry or use another tool.")
            output, status = client.run_turn(denial_thread, "Run the prescribed command once.", "rejection")
            assert status == "completed" and not marker.exists()
            assert any(a['decision'] == 'decline' for a in client.approvals)
            report['rejection'] = {'approval_declined': True, 'marker_absent': True, 'turn_status': status}

            cancellation_command = sleep_command(client.process_marker)

            cancellation_thread = start_thread(client, scratch, overrides, "never",
                "Use the shell tool once with the exact command: " + cancellation_command +
                " . Do not use other tools. After it finishes, reply exactly SLEEP-COMPLETE.", sandbox="workspace-write")
            output, status = client.run_turn(cancellation_thread,
                "Run the prescribed sleep command now. It must be executed, not described.", "cancellation")
            assert client.work_started, "Cancellation turn never started substantive work"
            assert client.cancel_response and "result" in client.cancel_response, client.cancel_response
            assert status == "interrupted", status
            assert "SLEEP-COMPLETE" not in output
            deadline = time.monotonic() + 5
            while any(process_alive(pid) for pid in client.running_pids) and time.monotonic() < deadline:
                time.sleep(.05)
            states = [process_state(pid) for pid in client.running_pids]
            report['cancellation_process_states'] = states
            report['command_metadata'] = client.command_metadata
            report['command_topology'] = client.command_topology
            report['cancellation'] = {'work_started': True, 'interrupt_acknowledged': True,
                'turn_status': status, 'parent_and_child_stopped': all(not process_alive(pid) for pid in client.running_pids)}
            assert all(not process_alive(pid) for pid in client.running_pids), {"cancellation_process_states": states}
            report["cancellation"] = {"work_started": True,
                "work_item_type": client.cancelled_item_type,
                "interrupt_acknowledged": True, "parent_and_child_stopped": True, "turn_status": status}
            report["passed"] = True
        finally:
            client.close()
            marker.unlink(missing_ok=True)
            outside.cleanup()
            report["bridge_exit"] = client.p.returncode
            collector.close()
            report["telemetry_requests"] = collector.requests
            report["telemetry_errors"] = collector.errors
            report["checked_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            client.temp.cleanup()
            print(json.dumps(report, indent=2))
        assert report["passed"] and report["bridge_exit"] == 0, report


if __name__ == "__main__":
    main()
