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

from routing import DEFAULT_ROUTES, EFFORTS, classify_agent_identity, select_route_details, has_attachments, user_text
from decision_engines import ENGINES, ENGINE_JEV, ENGINE_OLLAMA, ENGINE_PROVIDER, ENGINE_RULES, attachment_summary, build_state, candidate_routes, inline_images, run_jev, run_provider

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
        self.current_decisions = {}
        self.thread_categories = self.load_thread_categories()
        self.history_writes = 0
        self.stats = {"accepted": 0, "non_astra": 0}

    def load_thread_categories(self):
        """Recover only safe identity metadata, never prompt content, after restart."""
        categories = {}
        try:
            history = self.state_dir / "history.jsonl"
            if not history.exists():
                return categories
            for line in history.read_text(encoding="utf-8").splitlines()[-20000:]:
                record = json.loads(line)
                thread, category = record.get("thread"), record.get("agent_category")
                if thread and category:
                    categories[thread] = {"agent_category": category,
                                          "agent_confidence": record.get("agent_confidence", "heredada")}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        return categories

    def record_history(self, event, **fields):
        """Append privacy-safe decision metadata; never prompts, outputs or tool data."""
        allowed = {"decision_id", "thread", "title", "model", "effort", "previous_model",
                   "model_reason", "effort_reason", "agent_category", "agent_confidence", "source", "status", "signal", "error_type", "error_code",
                   "inputTokens", "outputTokens", "cachedInputTokens", "reasoningOutputTokens", "routing_engine", "engine_model",
                   "engine_status", "engine_confidence", "engine_latency_ms", "engine_failure", "engine_input_tokens",
                   "engine_output_tokens", "engine_cached_tokens", "proposed_model", "proposed_effort", "engine_active", "engine_applied"}
        record = {"schema": 2, "time": time.time(), "time_iso":
                  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event,
                  "session": str(os.getpid())}
        record.update({key: value for key, value in fields.items() if key in allowed and value is not None})
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            history = self.state_dir / "history.jsonl"
            with history.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            self.history_writes += 1
            if self.history_writes % 100 == 0 and history.stat().st_size > 5 * 1024 * 1024:
                self.prune_history(history)
        except OSError:
            pass

    def prune_history(self, history):
        try:
            days = int(read_config(self.config_path).get("history_days", 90))
            cutoff = 0 if days <= 0 else time.time() - days * 86400
            lines = history.read_text(encoding="utf-8").splitlines()
            kept = []
            for line in lines[-20000:]:
                try:
                    if float(json.loads(line).get("time", 0)) >= cutoff:
                        kept.append(line)
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
            temp = history.with_suffix(".tmp")
            temp.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
            os.replace(temp, history)
        except (OSError, ValueError, KeyError):
            pass

    def new_decision(self, tid, model, effort, model_reason, effort_reason, source, previous_model=None, signal=None,
                     agent_category=None, agent_confidence=None):
        previous_decision = self.current_decisions.get(tid)
        if previous_decision and signal == "retry":
            self.record_history("decision_signal", decision_id=previous_decision, thread=tid, signal="retry")
        elif previous_decision and source == "explicit" and previous_model != model:
            self.record_history("decision_signal", decision_id=previous_decision, thread=tid, signal="manual_override")
        decision_id = uuid.uuid4().hex
        title = self.threads.get(tid, {}).get("name") or (tid[:8] if tid else "Sin título")
        self.current_decisions[tid] = decision_id
        if agent_category:
            self.thread_categories[tid] = {"agent_category": agent_category,
                                           "agent_confidence": agent_confidence or "baja"}
        self.threads.setdefault(tid, {}).pop("tokens", None)
        self.record_history("decision_created", decision_id=decision_id, thread=tid, title=title,
                            model=model, effort=effort, previous_model=previous_model,
                            model_reason=model_reason, effort_reason=effort_reason, source=source,
                            agent_category=agent_category, agent_confidence=agent_confidence, status="pending")
        return decision_id

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
                            old = {**self.thread_categories.get(tid, {}), **self.threads.get(tid, {})}
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
                            if accepted:
                                error = message.get("error") or {}
                                self.record_history("decision_rejected", decision_id=accepted.get("decision_id"),
                                                    thread=tid, status="error", error_type="turn_rejected",
                                                    error_code=error.get("code"))
                        elif accepted:
                            self.threads.setdefault(tid, {}).update(**accepted, confirmation="Aceptado por Codex", status="inProgress", updated=time.time())
                            self.stats["accepted"] += 1
                            if accepted["model"] in {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
                                self.stats["non_astra"] += 1
                            self.log({"event": "turn_accepted", "thread": tid, **accepted})
                            self.record_history("decision_accepted", decision_id=accepted.get("decision_id"),
                                                thread=tid, title=self.threads.get(tid, {}).get("name"),
                                                model=accepted.get("model"), effort=accepted.get("effort"),
                                                status="inProgress")
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
                    row = self.threads.get(tid, {})
                    tokens = row.get("tokens") or {}
                    self.record_history("decision_completed", decision_id=self.current_decisions.get(tid),
                                        thread=tid, title=row.get("name"), status=row.get("status"), **tokens)
                elif method == "thread/name/updated":
                    self.threads.setdefault(tid, {})["name"] = params.get("threadName", params.get("name", tid))
                elif method == "thread/status/changed":
                    status = params.get("status", {}).get("type", "unknown")
                    self.threads.setdefault(tid, {}).update(status=status, updated=time.time())
                    if status in ("error", "failed", "interrupted"):
                        self.record_history("decision_error", decision_id=self.current_decisions.get(tid),
                                            thread=tid, title=self.threads.get(tid, {}).get("name"),
                                            status=status, error_type="thread_" + status)
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
                            parent = self.threads.get(item.get("senderThreadId"), {})
                            row.update(parent=item.get("senderThreadId"), updated=time.time())
                            if not row.get("agent_category") and parent.get("agent_category"):
                                row.update(agent_category=parent["agent_category"], agent_confidence="heredada")
                            if item.get("model") and row.get("confirmation") != "Aceptado por Codex":
                                row.update(model=item["model"], effort=item.get("reasoningEffort"), confirmation="Solicitado por agente")
                                if not row.get("decision_id"):
                                    row["decision_id"] = self.new_decision(receiver, item["model"], item.get("reasoningEffort"),
                                        "modelo solicitado por el agente coordinador",
                                        "nivel solicitado por el agente coordinador", "agent",
                                        agent_category=row.get("agent_category", "general"),
                                        agent_confidence=row.get("agent_confidence", "baja"))
                            agent = item.get("agentsStates", {}).get(receiver, {})
                            row["status"] = agent.get("status", "unknown") if isinstance(agent, dict) else "unknown"
                elif method == "thread/tokenUsage/updated":
                    usage = params.get("tokenUsage", {}).get("last", {})
                    tokens = {k: usage[k] for k in ("inputTokens", "outputTokens", "cachedInputTokens", "reasoningOutputTokens") if k in usage}
                    self.threads.setdefault(tid, {}).update(tokens=tokens, updated=time.time())
                    if self.current_decisions.get(tid):
                        self.record_history("decision_usage", decision_id=self.current_decisions[tid], thread=tid, **tokens)
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
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as error:
            with self.lock:
                self.log({"event": "preserved", "reason": "router_error"})
                self.record_history("router_error", error_type=type(error).__name__, status="error")
            return raw

    def observe_preserved(self, message):
        """Observe explicit settings even while paused; never label them routed."""
        params = message["params"]
        row = self.threads.get(params.get("threadId"), {})
        settings = (params.get("collaborationMode") or {}).get("settings") or {}
        model = settings.get("model") or params.get("model") or row.get("configured_model") or row.get("model")
        effort = settings.get("reasoning_effort") or params.get("effort") or row.get("configured_effort") or row.get("effort")
        if model:
            tid = params.get("threadId")
            items = params.get("input") if isinstance(params.get("input"), list) else []
            category, confidence = classify_agent_identity(user_text(items), row.get("name", ""), has_attachments(items),
                                                           previous=row.get("agent_category"))
            model_reason = "configuración original; sin intervención del selector"
            effort_reason = "nivel configurado manualmente en Codex"
            decision_id = self.new_decision(tid, model, effort, model_reason, effort_reason, "preserved",
                                            row.get("model"), agent_category=category, agent_confidence=confidence)
            self.accepted_routes[message["id"]] = {"model": model, "effort": effort, "reason": model_reason,
                "model_reason": model_reason, "effort_reason": effort_reason, "source": "preserved",
                "agent_category": category, "agent_confidence": confidence, "decision_id": decision_id}

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
        route, reasons = select_route_details(text, routes, previous, state.get("effort"), has_attachments(items))
        baseline_route, baseline_reasons = dict(route), dict(reasons)
        engine_name = config.get("routing_engine", ENGINE_RULES)
        # v15 called the first external connector "ollama". Keep existing users
        # working but record all new decisions under the product-level Provider.
        if engine_name == ENGINE_OLLAMA:
            engine_name = ENGINE_PROVIDER
        if engine_name not in ENGINES:
            engine_name = ENGINE_RULES
        candidates = candidate_routes(routes, self.catalog)
        external_allowed = (reasons.get("source") == "automatic" and not reasons["model"].startswith("continuación")
                            and bool(candidates))
        state_for_engine = build_state(text, attachment_summary(items), current, state.get("effort"), reasons.get("signal") == "retry")
        provider_settings = config.get("provider") or config.get("ollama") or {}
        provider_images = inline_images(items) if provider_settings.get("send_attachment_content", False) else []
        engine_result = {"engine": ENGINE_RULES, "status": "ok", "latency_ms": 0,
                         "route": {"model": route["model"], "effort": route["effort"]}, "engine_model": "local-policy"}
        if external_allowed and engine_name == ENGINE_JEV:
            engine_result = run_jev(config, self.state_dir, state_for_engine, candidates)
        elif external_allowed and engine_name == ENGINE_PROVIDER:
            engine_result = run_provider(config, self.state_dir, state_for_engine, candidates, provider_images)
        engine_applied = False
        if engine_result.get("engine") != ENGINE_RULES and engine_result.get("status") == "ok" and engine_result.get("route"):
            proposed = engine_result["route"]
            # Hard local policy remains a floor for visual work, attachments, audits and risk.
            strict = baseline_reasons["model"].startswith(("auditoría", "diseño de interfaces", "interpretación de adjuntos"))
            tiers = ("simple", "normal", "complex", "critical")
            chosen_tier = proposed.get("tier") or next((tier for tier, item in routes.items() if item["model"] == proposed["model"]), "simple")
            baseline_tier = next((tier for tier, item in routes.items() if item["model"] == baseline_route["model"]), "simple")
            if not strict or tiers.index(chosen_tier) >= tiers.index(baseline_tier):
                route = {"model": proposed["model"], "effort": proposed["effort"]}
                engine_applied = True
                label = "Jev" if engine_name == ENGINE_JEV else "Proveedor"
                reasons["model"] = "%s eligió %s para esta petición" % (label, proposed.get("label", route["model"]))
                reasons["effort"] = "%s propuso este nivel de razonamiento para la complejidad observada" % label
            else:
                engine_result["status"] = "guardrail"
        elif engine_name != ENGINE_RULES and external_allowed:
            label = "Jev" if engine_name == ENGINE_JEV else "Proveedor"
            failure = {"invalid": "respondió sin una elección única válida",
                       "not_configured": "no está configurado"}.get(engine_result.get("status"), "no estuvo disponible")
            reasons["model"] = "%s %s; se aplicó la política local: %s" % (label, failure, baseline_reasons["model"])
            reasons["effort"] = "respaldo local: " + baseline_reasons["effort"]
        # The configured engine may have been attempted, but local policy owns
        # the final selection after a malformed response, failure or guardrail.
        effective_engine = engine_result.get("engine", ENGINE_RULES) if engine_applied else ENGINE_RULES
        category, confidence = classify_agent_identity(text, state.get("name", ""), has_attachments(items),
                                                       reasons["model"], state.get("agent_category"))
        model, effort = route["model"], route["effort"]
        if effort == "ultra" and model in self.catalog and effort not in self.catalog[model] and "max" in self.catalog[model]:
            effort = "max"
            reasons["effort"] += "; Ultra no está disponible para este modelo, se utiliza Máx."
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
        decision_id = self.new_decision(tid, model, effort, reasons["model"], reasons["effort"], reasons["source"],
                                        current, reasons.get("signal"), category, confidence)
        self.record_engine_comparisons(config, decision_id, tid, candidates, state_for_engine, provider_images, engine_name,
                                       engine_result, baseline_route, external_allowed)
        self.record_history("decision_routed", decision_id=decision_id, thread=tid, model=model, effort=effort,
                            routing_engine=effective_engine, engine_applied=engine_applied)
        decision = {"model": model, "effort": effort, "reason": reasons["model"],
                    "model_reason": reasons["model"], "effort_reason": reasons["effort"],
                    "source": reasons["source"], "agent_category": category,
                    "agent_confidence": confidence, "decision_id": decision_id,
                    "routing_engine": effective_engine, "engine_model": engine_result.get("engine_model"),
                    "engine_status": engine_result.get("status"), "engine_confidence": engine_result.get("confidence"),
                    "engine_latency_ms": engine_result.get("latency_ms"), "engine_applied": engine_applied}
        self.threads.setdefault(tid, {}).update(tier=tier, seen_turn=True, requested_model=model,
                                              requested_effort=effort, status="pending", updated=time.time(), **decision)
        if "id" in message:
            self.accepted_routes[message["id"]] = decision
        if config.get("sync_picker", True) and "id" in message:
            self.sync_after_ack[message["id"]] = {"threadId": tid, "model": model, "effort": effort}
        self.log({"event": "routed", "thread": tid, "from": current, "model": model,
                  "effort": effort, "reason": reasons["model"], "effort_reason": reasons["effort"],
                  "decision_id": decision_id, "routing_engine": effective_engine, "engine_status": engine_result.get("status")})
        return (json.dumps(changed, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

    def record_engine_comparisons(self, config, decision_id, tid, candidates, state, provider_images, active_engine, active_result, baseline_route, allowed):
        """Record comparable, content-free engine choices. Shadow engines never affect Codex."""
        results = [active_result]
        shadows = config.get("comparison_engines") or []
        seen = {active_result.get("engine", ENGINE_RULES), active_engine}
        if allowed:
            for name in shadows:
                if name == ENGINE_OLLAMA:
                    name = ENGINE_PROVIDER
                if name not in ENGINES or name in seen:
                    continue
                seen.add(name)
                if name == ENGINE_RULES:
                    results.append({"engine": ENGINE_RULES, "status": "ok", "latency_ms": 0,
                                    "route": baseline_route, "engine_model": "local-policy"})
                elif name == ENGINE_JEV:
                    results.append(run_jev(config, self.state_dir, state, candidates))
                elif name == ENGINE_PROVIDER:
                    results.append(run_provider(config, self.state_dir, state, candidates, provider_images))
        for index, result in enumerate(results):
            proposed = result.get("route") or baseline_route
            self.record_history("engine_comparison", decision_id=decision_id, thread=tid, routing_engine=result.get("engine", ENGINE_RULES),
                                engine_active=index == 0, engine_model=result.get("engine_model"), engine_status=result.get("status"),
                                engine_confidence=result.get("confidence"), engine_latency_ms=result.get("latency_ms"),
                                engine_failure=result.get("engine_failure"), engine_input_tokens=result.get("engine_input_tokens"),
                                engine_output_tokens=result.get("engine_output_tokens"), engine_cached_tokens=result.get("engine_cached_tokens"),
                                proposed_model=proposed.get("model"), proposed_effort=proposed.get("effort"))


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
        if proc.returncode:
            router.record_history("bridge_error", status="error", error_type="backend_exit",
                                  error_code=proc.returncode)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
