"""Opt-in isolated end-to-end checkpoint probe, using the subscription.

Creates one synthetic durable task (dynamic tools cannot be registered on an
existing task), then archives it. Never restarts Desktop or changes live config.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib

from smoke_native import Client, ROOT
from desktop_runtime import discover
from routing import DEFAULT_ROUTES
from platform_support import with_loopback_telemetry
from probe_model_compatibility import Collector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required: one synthetic subscription turn")
    install = discover()
    overrides = {"features.shell_tool": False, "features.web_search": False,
        "features.code_mode": True, "features.code_mode_host": True,
        "features.apps": False, "features.multi_agent": False}
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if config.exists():
        for name in tomllib.loads(config.read_text(encoding="utf-8-sig")).get("mcp_servers", {}):
            overrides["mcp_servers." + name + ".enabled"] = False
    with tempfile.TemporaryDirectory(prefix="router-phase-bridge-") as folder:
        root = Path(folder)
        settings = root / "config.json"
        settings.write_text(json.dumps({"installation_mode": "auto", "enabled": True,
            "phase_routing": True, "sync_picker": False, "inference_telemetry": False,
            "routing_engine": "rules", "comparison_engines": [], "routes": DEFAULT_ROUTES}))
        command = [sys.executable, str(ROOT / "router.py")]
        for key, value in overrides.items():
            command += ["-c", key + "=" + json.dumps(value)]
        command += ["app-server"]
        collector = Collector()
        endpoint = "http://127.0.0.1:" + str(collector.server.server_port) + "/v1/logs"
        command = command[:2] + with_loopback_telemetry(command[2:], endpoint, collector.token)
        client = Client(command, {"PERSONAL_CODEX_ROUTER_CONFIG": str(settings)})
        tid = None
        report = {"desktop_version": install.version, "scope": "isolated bridge, synthetic archived task",
                  "passed": False, "archived": False}
        try:
            client.call("initialize", {"clientInfo": {"name": "personal_phase_bridge_probe", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True}})
            client.send({"method": "initialized", "params": {}})
            assert (client.call("account/read", {"refreshToken": False}).get("account") or {}).get("type") == "chatgpt"
            client.call("model/list", {"limit": 100})
            created = client.call("thread/start", {"cwd": folder, "model": "gpt-5.6-terra",
                "modelProvider": "openai", "sandbox": "read-only", "approvalPolicy": "never",
                "baseInstructions": "Synthetic protocol test, not project work. Use only router_phase_checkpoint when requested. Await it alone. In code mode use text(await tools.router_phase_checkpoint({phase:'verify',complexity:'complex'})). No other tools, files, shell or network. Return exactly the requested checkpoint and the status returned by the tool.",
                "developerInstructions": "Isolated synthetic test. Do not perform project work."})
            tid = created["thread"]["id"]
            client.call("thread/name/set", {"threadId": tid, "name": "Synthetic router phase bridge probe"})
            output = client.turn(tid, "Remember CODE-37. Call router_phase_checkpoint once using the arguments prescribed in the test instructions. Then reply exactly CODE-37 followed by a space and the status returned by the tool.")
            history = client.state / "history.jsonl"
            records = [json.loads(line) for line in history.read_text().splitlines()] if history.exists() else []
            checkpoints = [r for r in records if r.get("event") == "phase_checkpoint"]
            report["checkpoint_statuses"] = [r["phase_status"] for r in checkpoints]
            accepted = next(r for r in records if r.get("event") == "decision_accepted" and r.get("thread") == tid)
            report["initial_model"] = accepted["model"]
            report["initial_effort"] = accepted["effort"]
            report["evidence_scope"] = "single synthetic turn in isolated backend; native telemetry without guaranteed turn identifiers"
            report["output_matches"] = output.strip().strip(".") == "CODE-37 applied"
            assert report["checkpoint_statuses"] == ["requested", "applied"], report
            assert report["output_matches"], "Unexpected synthetic output"
            assert client.tool_calls == 0, "Owned tool leaked to hosting client"
        finally:
            if tid:
                try:
                    client.call("thread/archive", {"threadId": tid})
                    report["archived"] = True
                except (RuntimeError, TimeoutError):
                    report["archived"] = False
            client.close()
            collector.close()
            observed = sorted((r for r in collector.events if r.get("event.kind") == "response.completed"),
                              key=lambda r: int(r["time_unix_nano"]))
            report["native_inferences"] = [{k: r[k] for k in ("model", "model_reasoning_effort") if k in r} for r in observed]
            report["telemetry_errors"] = collector.errors
            report["telemetry_requests"] = collector.requests
            report["exit_code"] = client.p.returncode
            client.temp.cleanup()
            initial = (report.get("initial_model"), report.get("initial_effort"))
            pairs = [(r.get("model"), r.get("model_reasoning_effort")) for r in observed]
            report["passed"] = (initial[0] != "gpt-5.6-sol" and initial in pairs
                and ("gpt-5.6-sol", "high") in pairs and report.get("output_matches", False)
                and report.get("checkpoint_statuses") == ["requested", "applied"])
            (ROOT / "state" / "phase-bridge-probe.json").write_text(json.dumps(report, indent=2) + "\n")
        assert report["passed"] and report["archived"] and report["exit_code"] == 0, report
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
