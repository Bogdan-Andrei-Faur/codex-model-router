"""Transparent JSONL bridge to the installed Codex app-server on Windows.

Only model/effort in eligible turn/start requests are changed. All other bytes
and server output are forwarded. No credential loading, network gateway, prompt
replay, transcript editing, or additional model requests are involved.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from routing import DEFAULT_ROUTES, EFFORTS, select_route, has_attachments, user_text

ROOT = Path(__file__).resolve().parent


def read_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


class Router:
    def __init__(self, config_path, state_dir=None):
        self.config_path = Path(config_path)
        self.state_dir = Path(state_dir) if state_dir else ROOT / "state"
        self.catalog = {}
        self.requests = {}
        self.threads = {}
        self.active = set()
        self.pending = set()
        self.lock = threading.RLock()
        self.events = []
        self.sync_after_ack = {}
        self.internal_requests = set()
        self.outbound = []
        self.accepted_routes = {}
        self.stats = {"accepted": 0, "non_astra": 0}

    def log(self, event):
        # The small diagnostic file never contains prompt text, input, auth, paths
        # from messages, tool arguments, or model output.
        event = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
        self.events.append(event)
        self.events = self.events[-100:]
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            target = self.state_dir / ("status-%s.json" % os.getpid())
            temp = target.with_suffix(".tmp")
            temp.write_text(json.dumps({"version": 2, "pid": os.getpid(), "events": self.events,
                                       "heartbeat": time.time(), "threads": self.threads,
                                       "catalog": {m: sorted(e) for m, e in self.catalog.items()},
                                       "stats": self.stats},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, target)
        except OSError:
            pass  # Diagnostics must never break a user's message.

    def server_line(self, raw):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                return
            with self.lock:
                if "method" not in message and message.get("id") in self.internal_requests:
                    self.internal_requests.discard(message["id"])
                    if "error" in message:
                        self.log({"event": "display_sync_unavailable"})
                    return False
                request = (self.requests.pop(message.get("id"), None)
                           if "method" not in message else None)
                if request:
                    method, params = request
                    result = message.get("result") or {}
                    if method == "model/list" and "error" not in message:
                        for model in result.get("data", []):
                            self.catalog[model["model"]] = {
                                e["reasoningEffort"] for e in model.get("supportedReasoningEfforts", [])}
                    elif method in ("thread/start", "thread/resume", "thread/read"):
                        thread = result.get("thread") or {}
                        tid = thread.get("id")
                        if tid:
                            old = self.threads.get(tid, {})
                            self.threads[tid] = {**old,
                                "provider": result.get("modelProvider", thread.get("modelProvider", old.get("provider"))),
                                "model": old.get("model") if old.get("confirmation") == "Aceptado por Codex" else result.get("model", thread.get("model", old.get("model"))),
                                "name": thread.get("name") or thread.get("agentNickname") or old.get("name") or tid[:8],
                                "parent": thread.get("parentThreadId"),
                                "effort": old.get("effort") if old.get("confirmation") == "Aceptado por Codex" else result.get("reasoningEffort") or thread.get("reasoningEffort") or old.get("effort"),
                                "status": thread.get("status", {}).get("type", "unknown"),
                                "confirmation": old.get("confirmation", "Configurado; sin envío observado"),
                                "seen_turn": old.get("seen_turn", method != "thread/start")}
                            if thread.get("status", {}).get("type") == "active":
                                self.active.add(tid)
                    elif method == "turn/start":
                        tid = params.get("threadId")
                        self.pending.discard(tid)
                        sync = self.sync_after_ack.pop(message.get("id"), None)
                        accepted = self.accepted_routes.pop(message.get("id"), None)
                        if "error" in message:
                            self.threads.setdefault(tid, {}).update(**(accepted or {}), status="error", confirmation="Rechazado")
                            self.log({"event": "turn_rejected", "thread": tid})
                        elif accepted:
                            self.threads.setdefault(tid, {}).update(**accepted, confirmation="Aceptado por Codex", status="inProgress", updated=time.time())
                            self.stats["accepted"] += 1
                            if accepted["model"] in {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
                                self.stats["non_astra"] += 1
                            self.log({"event": "turn_accepted", "thread": tid, **accepted})
                        if "error" not in message and sync:
                            # After acknowledgement, turn/start has already applied
                            # the user's mode and permissions. Ask the native server
                            # to publish its actual settings to the Desktop picker.
                            rid = "personal-router-" + uuid.uuid4().hex
                            self.internal_requests.add(rid)
                            self.outbound.append({"id": rid, "method": "thread/settings/update", "params": sync})
                method = message.get("method")
                params = message.get("params") or {}
                tid = params.get("threadId")
                if method == "turn/started":
                    self.active.add(tid)
                    self.threads.setdefault(tid, {}).update(status="inProgress", updated=time.time())
                elif method == "turn/completed":
                    self.active.discard(tid)
                    self.pending.discard(tid)
                    self.threads.setdefault(tid, {}).update(status=params.get("turn", {}).get("status", "completed"), updated=time.time())
                    self.log({"event": "turn_completed", "thread": tid})
                elif method == "thread/name/updated":
                    self.threads.setdefault(tid, {})["name"] = params.get("threadName", params.get("name", tid))
                elif method == "thread/status/changed":
                    self.threads.setdefault(tid, {}).update(status=params.get("status", {}).get("type", "unknown"), updated=time.time())
                elif method == "thread/started":
                    thread = params.get("thread", {})
                    if thread.get("id"):
                        row = self.threads.setdefault(thread["id"], {})
                        row.update(name=thread.get("name") or thread.get("agentNickname") or thread["id"][:8],
                                   parent=thread.get("parentThreadId"), updated=time.time())
                        if thread.get("model"):
                            row.setdefault("model", thread["model"])
                            row.setdefault("effort", thread.get("reasoningEffort"))
                            row.setdefault("confirmation", "Configurado; sin envío observado")
                elif method in ("item/started", "item/completed"):
                    item = params.get("item", {})
                    if item.get("type") == "collabAgentToolCall":
                        for receiver in item.get("receiverThreadIds", []):
                            row = self.threads.setdefault(receiver, {})
                            row.update(parent=item.get("senderThreadId"), updated=time.time())
                            if item.get("model") and row.get("confirmation") != "Aceptado por Codex":
                                row.update(model=item["model"], effort=item.get("reasoningEffort"), confirmation="Solicitado por agente")
                            agent = item.get("agentsStates", {}).get(receiver, {})
                            row["status"] = agent.get("status", "unknown") if isinstance(agent, dict) else "unknown"
                elif method == "thread/tokenUsage/updated":
                    usage = params.get("tokenUsage", {}).get("last", {})
                    self.threads.setdefault(tid, {})["tokens"] = {k: usage[k] for k in ("inputTokens", "outputTokens", "cachedInputTokens", "reasoningOutputTokens") if k in usage}
                elif method == "thread/settings/updated":
                    settings = params.get("threadSettings") or {}
                    state = self.threads.setdefault(tid, {})
                    if settings.get("model"):
                        state["configured_model"] = settings["model"]
                        state["configured_effort"] = settings.get("effort")
                        if not state.get("confirmation") == "Aceptado por Codex":
                            state.update(model=settings["model"], effort=settings.get("effort"))
                        self.log({"event": "native_settings", "thread": tid,
                                  "model": settings["model"], "effort": settings.get("effort")})
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
        return True

    def drain_outbound(self):
        with self.lock:
            result, self.outbound = self.outbound, []
            return result

    def client_line(self, raw):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                return raw
            method = message.get("method")
            params = message.get("params") or {}
            if not isinstance(params, dict):
                return raw
            with self.lock:
                if "id" in message and method in (
                        "model/list", "thread/start", "thread/resume", "thread/read", "turn/start"):
                    self.requests[message["id"]] = (method, params)
                if method != "turn/start":
                    return raw
                tid = params.get("threadId")
                if tid in self.active or tid in self.pending:
                    self.log({"event": "preserved", "reason": "active_turn", "thread": tid})
                    return raw
                self.pending.add(tid)
                routed = self.route_turn(message, raw)
                if routed == raw and "id" in message:
                    self.observe_preserved(message)
                return routed
        except (ValueError, KeyError, TypeError, AttributeError, OSError):
            with self.lock:
                self.log({"event": "preserved", "reason": "router_error"})
            return raw

    def observe_preserved(self, message):
        """Observe explicit settings even while paused; never label them routed."""
        params = message["params"]
        row = self.threads.get(params.get("threadId"), {})
        settings = (params.get("collaborationMode") or {}).get("settings") or {}
        model = settings.get("model") or params.get("model") or row.get("configured_model") or row.get("model")
        effort = settings.get("reasoning_effort") or params.get("effort") or row.get("configured_effort") or row.get("effort")
        if model:
            self.accepted_routes[message["id"]] = {"model": model, "effort": effort, "reason": "configuración original; sin intervención del selector"}

    def route_turn(self, message, raw):
        params = message["params"]
        tid = params.get("threadId")
        config = read_config(self.config_path)
        if not config.get("enabled", False):
            self.log({"event": "preserved", "thread": tid, "reason": "disabled"})
            return raw
        state = self.threads.get(tid, {})
        mode = params.get("collaborationMode") or {}
        settings = mode.get("settings") or {}
        current = settings.get("model") or params.get("model") or state.get("model")
        routes = config.get("routes", DEFAULT_ROUTES)
        owned_models = {r["model"] for r in routes.values()}
        # Do not move an Ollama/provider conversation to paid ChatGPT implicitly.
        if state.get("provider") != "openai" or current not in owned_models:
            self.log({"event": "preserved", "thread": tid, "reason": "other_or_unknown_provider"})
            return raw
        items = params.get("input")
        if not isinstance(items, list) or params.get("toolOutput") is not None:
            return raw
        text = user_text(items)
        if not text.strip():
            self.log({"event": "preserved", "thread": tid, "reason": "no_text"})
            return raw
        previous = state.get("tier")
        if previous is None:
            previous = next((t for t, r in routes.items() if r["model"] == current), None)
            # A fresh thread's default Astra isn't evidence of a complex task.
            if not state.get("seen_turn"):
                previous = None
        route, reason = select_route(text, routes, previous, state.get("effort"), has_attachments(items))
        model, effort = route["model"], route["effort"]
        if effort == "ultra" and model in self.catalog and effort not in self.catalog[model] and "max" in self.catalog[model]:
            effort = "max"
            reason += "; Ultra no disponible para este modelo: Máx."
        if effort not in self.catalog.get(model, set()):
            self.log({"event": "preserved", "thread": tid, "reason": "catalog_unavailable"})
            return raw
        changed = copy.deepcopy(message)
        changed["params"]["model"] = model
        changed["params"]["effort"] = effort
        if "collaborationMode" in params and params["collaborationMode"] is not None:
            changed["params"]["collaborationMode"]["settings"]["model"] = model
            changed["params"]["collaborationMode"]["settings"]["reasoning_effort"] = effort
        tier = next(t for t, r in routes.items() if r["model"] == model)
        self.threads.setdefault(tid, {}).update(tier=tier, seen_turn=True, requested_model=model,
                                              requested_effort=effort, status="pending", reason=reason, updated=time.time())
        if "id" in message:
            self.accepted_routes[message["id"]] = {"model": model, "effort": effort, "reason": reason}
        if config.get("sync_picker", True) and "id" in message:
            self.sync_after_ack[message["id"]] = {"threadId": tid, "model": model, "effort": effort}
        self.log({"event": "routed", "thread": tid, "from": current, "model": model,
                  "effort": effort, "reason": reason})
        return (json.dumps(changed, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def copy_bytes(source, target):
    try:
        while True:
            data = source.read1(65536) if hasattr(source, "read1") else source.read(65536)
            if not data:
                break
            target.write(data)
            target.flush()
    except (BrokenPipeError, OSError):
        pass


def main():
    config_path = Path(os.environ.get("PERSONAL_CODEX_ROUTER_CONFIG", ROOT / "config.local.json"))
    try:
        config = read_config(config_path)
        binary = Path(config["codex"]).resolve(strict=True)
        if binary.name.lower() != "codex.exe":
            raise ValueError("Unexpected backend filename")
    except (ValueError, KeyError, OSError):
        # Don't expose config or credential-bearing arguments in diagnostics.
        print("Personal router: backend configuration is unavailable.", file=sys.stderr)
        return 1
    args = sys.argv[1:]
    # Other CLI commands, including version/schema, remain the original program.
    is_server = "app-server" in args and not any(
        x in args for x in ("daemon", "proxy", "generate-ts", "generate-json-schema"))
    env = dict(os.environ)
    env.pop("PERSONAL_CODEX_ROUTER_CONFIG", None)
    # Desktop removes this identity when it sees a custom executable. Our child
    # is still its original installed engine, so preserve that original identity.
    family = config.get("windows_sandbox_package_family")
    if family:
        env["CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY"] = family
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    if not is_server:
        return subprocess.call([str(binary), *args], env=env, creationflags=flags,
                               stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
    if any(x.startswith(("ws://", "unix://")) for x in args):
        return subprocess.call([str(binary), *args], env=env, creationflags=flags,
                               stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
    proc = subprocess.Popen([str(binary), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, creationflags=flags)
    router = Router(config_path)
    router.log({"event": "bridge_started", "backend_pid": proc.pid})
    heartbeat_stop = threading.Event()
    def heartbeat_worker():
        while not heartbeat_stop.wait(2):
            with router.lock:
                # Keep liveness fresh without growing the event history.
                previous_events = list(router.events)
                router.log({"event": "heartbeat"})
                router.events = previous_events
    threading.Thread(target=heartbeat_worker, daemon=True).start()
    write_lock = threading.Lock()

    def write_native(data):
        with write_lock:
            proc.stdin.write(data)
            proc.stdin.flush()

    def input_worker():
        try:
            for line in sys.stdin.buffer:
                write_native(router.client_line(line))
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                with write_lock:
                    proc.stdin.close()
            except OSError:
                pass

    threading.Thread(target=input_worker, daemon=True).start()
    stderr_worker = threading.Thread(target=copy_bytes, args=(proc.stderr, sys.stderr.buffer), daemon=True)
    stderr_worker.start()
    try:
        for line in proc.stdout:
            forward = router.server_line(line)
            if forward is not False:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            for command in router.drain_outbound():
                try:
                    write_native((json.dumps(command) + "\n").encode())
                except (ValueError, BrokenPipeError, OSError):
                    pass
    except (BrokenPipeError, OSError):
        if proc.poll() is None:
            proc.terminate()
    finally:
        heartbeat_stop.set()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
        stderr_worker.join(timeout=1)
        router.log({"event": "bridge_stopped", "exit_code": proc.returncode})
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
