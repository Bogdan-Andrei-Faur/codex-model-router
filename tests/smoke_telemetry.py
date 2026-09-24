"""Isolated native telemetry regression probe; --live sends a tiny test turn.

Never reads conversations or stores raw telemetry. Starts only ephemeral test
threads with tools disabled. Without --live, no model inference is requested.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_runtime import discover
from inference_telemetry import LocalInferenceTelemetry
from platform_support import with_loopback_telemetry
from smoke_native import Client


def probe(binary, layout, live=False):
    events = []
    collector = LocalInferenceTelemetry(events.append)
    client = None
    try:
        overrides = {"features.shell_tool": False, "features.web_search": False,
                     "features.apps": False, "features.multi_agent": False,
                     "features.code_mode": False, "features.code_mode_host": False}
        config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
        if config.exists():
            for name in tomllib.loads(config.read_text(encoding="utf-8-sig")).get("mcp_servers", {}):
                overrides["mcp_servers." + name + ".enabled"] = False
        args = []
        for key, value in overrides.items():
            args += ["-c", key + "=" + json.dumps(value)]
        if layout == "subcommand":
            args = ["app-server", *args]
        elif layout == "desktop":
            args = ["-c", 'model_reasoning_effort="high"', "app-server", *args,
                    "--analytics-default-enabled", "-c", "bundled.mcp_servers.codex_app.enabled=false"]
        else:
            args += ["app-server"]
        command = [str(binary), *with_loopback_telemetry(args, collector.endpoint)]
        client = Client(command)
        client.call("initialize", {"clientInfo": {"name": "router_telemetry_probe", "version": "0.2.0"}})
        client.send({"method": "initialized", "params": {}})
        effective = client.call("config/read", {"includeLayers": False})["config"]
        for key, value in overrides.items():
            node = effective
            for part in key.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            if node is not value:
                raise AssertionError("Injection changed unrelated native configuration")
        config = effective.get("otel") or {}
        exporter = config.get("exporter") or {}
        if not isinstance(exporter, dict) or (exporter.get("otlp-http") or {}).get("endpoint") != collector.endpoint:
            raise AssertionError("Native config discarded the local OTel endpoint")
        if config.get("log_user_prompt") is not False:
            raise AssertionError("Native config did not disable prompt logging")
        with tempfile.TemporaryDirectory(prefix="router-telemetry-", ignore_cleanup_errors=True) as folder:
            result = client.call("thread/start", {"ephemeral": True, "cwd": folder,
                "model": "gpt-5.6-luna", "modelProvider": "openai",
                "sandbox": "read-only", "approvalPolicy": "never"})
            if live:
                tid = result["thread"]["id"]
                turn = client.call("turn/start", {"threadId": tid, "model": "gpt-5.6-luna", "effort": "low",
                    "input": [{"type": "text", "text": "Reply only with OK. Do not use any tools."}]})
                buffered, client.notifications = client.notifications, []
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    event = buffered.pop(0) if buffered else client.next(max(.1, deadline-time.monotonic()))
                    if event.get("method") == "turn/completed" and event.get("params", {}).get("turn", {}).get("id") == turn["turn"]["id"]:
                        if event["params"]["turn"]["status"] != "completed":
                            raise RuntimeError("Synthetic turn failed")
                        break
                else:
                    raise TimeoutError("Synthetic turn did not complete")
            deadline = time.monotonic() + 7
            while time.monotonic() < deadline:
                if (any(e.get("event_kind") == "response.completed" for e in events) if live else collector.snapshot()["requests"] > 0):
                    break
                time.sleep(.2)
            before = collector.snapshot()
        client.close()
        client = None
        if not before["requests"]:
            raise AssertionError("Native runtime emitted no telemetry before shutdown")
        if live and not any(e.get("event_kind") == "response.completed" for e in events):
            raise AssertionError("No completed inference was observed")
        return {"layout": layout, "native_config_verified": True, "live": live, "before_shutdown": before,
                "after_shutdown": collector.snapshot(), "completed_events": sum(e.get("event_kind") == "response.completed" for e in events)}
    finally:
        if client:
            client.close()
        collector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--layout", choices=("root", "subcommand", "desktop"), action="append", dest="layouts")
    options = parser.parse_args()
    install = discover()
    print(json.dumps({"desktop_version": install.version}), flush=True)
    for layout in options.layouts or ["root", "subcommand", "desktop"]:
        print(json.dumps(probe(install.backend, layout, options.live)), flush=True)


if __name__ == "__main__":
    main()
