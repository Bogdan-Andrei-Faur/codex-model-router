"""Transparent JSONL bridge to the installed Codex app-server on Windows/macOS.

Model/effort in eligible turn/start requests are changed. The opt-in phase
controller also owns an isolated dynamic tool and native settings RPCs.
Optional JEV classification receives a transient
request and content-free context; it has a bounded local fallback. No transcript
editing or additional Codex inference is performed.
"""
import copy
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from routing import DEFAULT_ROUTES, EFFORTS, TIERS, classify_agent_identity, select_route_details, has_attachments, user_text, summarize_response_context
from decision_engines import ENGINES, ENGINE_JEV, ENGINE_RULES, attachment_summary, build_state, candidate_routes, run_jev
from thread_inventory import ThreadInventory, thread_metadata
from platform_support import backend_path, creation_flags, uses_stdio, stop_backend, input_lines, with_loopback_telemetry, with_server_overrides
from desktop_runtime import discover
from task_modes import read_mode
from phase_tracking import phase_update, proposed_phase, native_plan
from inference_telemetry import LocalInferenceTelemetry
from inference_attribution import COUNTERS as ATTRIBUTION_COUNTERS, COMPLETION_FIELDS, attribute
from workload import effective_context, merge_contract, plan_steps, context_for_engine, resumes_work, cancels_work
from state_store import (recover_tasks, persist_task, append_record, append_prompt_record,
                         compact_history, compact_prompt_history, atomic_json, private_directory)
from build_identity import identity, router_identity, POLICY_VERSION
from request_dispatch import Dispatcher
from phase_control import PhaseController
from error_diagnostics import DIAGNOSTIC_FIELDS, native_error, rpc_error, clear_error
from process_control import CommandProcesses
from model_catalog import MODELS, migrate_config, available_routes, estimate_standard_usage, CATALOG_VERSION
from usage_state import AccountUsage, context_window, update_context_compaction
import candidate_policy
from application_layout import code_root, data_root

CODE_ROOT = code_root()
ROOT = data_root(CODE_ROOT)
BUILD = identity(CODE_ROOT)
PRODUCT_VERSION = BUILD[0]
ROUTER_BUILD = router_identity(CODE_ROOT)
SHADOW_SLOTS = threading.BoundedSemaphore(2)


def read_config(path):
    return migrate_config(json.loads(Path(path).read_text(encoding="utf-8-sig")))


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
        self.runtime_instance = uuid.uuid4().hex
        self.native_errors = {}
        self.temporary_threads = set()
        self.thread_categories = self.load_thread_categories()
        self.history_writes = 0
        self.prompt_writes = 0
        self.next_retention_check = 0
        self.stats = {"accepted": 0, "non_astra": 0, "telemetry_events": 0,
                      "telemetry_confirmed": 0, "telemetry_unattributed": 0}
        self.stats.update(dict.fromkeys(ATTRIBUTION_COUNTERS, 0))
        self.inventory = ThreadInventory()
        self.client_name = "unknown"
        self.handshake_complete = False
        self.account_usage = AccountUsage()
        self.telemetry = None
        self.inference_ids = set()
        self.metric_buckets = {}
        self.phases = PhaseController(self, self.phase_config().get("phase_routing") is True)
        self.commands = CommandProcesses()

    def confirm_restart_settings(self, config, telemetry_enabled):
        """Clear the UI reminder only after this bridge loaded requested settings."""
        desired = {"phase_routing": config.get("phase_routing") is True,
                   "inference_telemetry": config.get("inference_telemetry") is True}
        loaded = {"phase_routing": self.phases.enabled is True,
                  "inference_telemetry": telemetry_enabled is True}
        if desired != loaded:
            return False
        try:
            (self.state_dir / "restart-required.json").unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def stop_commands(self, commands):
        for command in commands:
            rid = "personal-router-cancel-" + uuid.uuid4().hex
            self.internal_requests.add(rid)
            self.outbound.append({"id": rid,
                "method": "thread/backgroundTerminals/terminate",
                "params": {"threadId": command.thread, "processId": command.process_id}})

    def phase_config(self):
        try:
            return read_config(self.config_path)
        except (OSError, ValueError):
            return {}  # Pausing or damaged configuration must fail closed.

    def set_telemetry(self, collector):
        self.telemetry = collector

    def load_thread_categories(self):
        """Recover only safe identity/workload metadata, never prompt content, after restart."""
        categories = recover_tasks(self.state_dir)
        for thread, row in categories.items():
            try:
                persist_task(self.state_dir, thread, row, only_if_missing=True)
            except OSError:
                pass
        return categories

    def save_task(self, tid, row):
        if tid in self.temporary_threads:
            return
        try:
            persist_task(self.state_dir, tid, row)
        except OSError:
            self.log({"event": "task_state_unavailable", "thread": tid})

    def clear_pending_phase(self, tid):
        row = self.threads.get(tid, {})
        for source in (row, self.thread_categories.get(tid, {})):
            for key in ("pending_phase_floor", "pending_phase_name", "pending_phase_id"):
                source.pop(key, None)
        self.save_task(tid, row)

    def record_history(self, event, **fields):
        """Append privacy-safe decision metadata; never prompts, outputs or tool data."""
        if fields.get("thread") in self.temporary_threads:
            return
        allowed = {"decision_id", "thread", "title", "model", "effort", "previous_model",
                   "model_reason", "effort_reason", "agent_category", "agent_confidence", "source", "status", "signal", "error_type", "error_code",
                   "inputTokens", "outputTokens", "cachedInputTokens", "reasoningOutputTokens", "routing_engine", "engine_model",
                   "engine_status", "engine_confidence", "engine_latency_ms", "engine_failure", "engine_input_tokens",
                   "engine_output_tokens", "engine_cached_tokens", "proposed_model", "proposed_effort", "engine_active", "engine_applied", "task_mode",
                   "continuity_strategy", "phase_name", "phase_status", "phase_model", "phase_effort",
                   "phase_transition", "observed_model", "observed_effort", "configured_model", "configured_effort",
                   "accepted_model", "accepted_effort", "pipeline_mode", "phase_pipeline", "inference_source",
                   "model_quality", "effort_quality", "routing_policy_version", "request_kind", "quality_floor", "quality_ceiling", "max_effort_allowed",
                   "task_floor", "min_effort", "evidence_confidence", "turn_id", "error_http_status", "error_source", "will_retry"}
        allowed.update({"inference_input_tokens", "inference_output_tokens", "inference_cached_tokens",
                        "inference_cache_write_tokens", "inference_reasoning_tokens", "inference_tool_tokens",
                        "inference_duration_ms", "inference_ttft_ms", "inference_attempt",
                        "inference_http_status", "inference_success", "observed_candidate_model", "observed_candidate_effort"})
        allowed.update({"phase_id", "phase_source_model", "inference_event_name", "inference_event_kind", "inference_event_id", "inference_timestamp_source"})
        allowed.update({"inference_sample_count", "inference_failure_count", "estimated_api_standard_usd",
                        "estimated_codex_standard_credits", "estimate_basis", "estimate_rates_version"})
        allowed.update({'expected_model', 'expected_effort', 'inference_model_mismatch', 'inference_effort_mismatch'})
        allowed.update(('phase_source_effort', 'phase_complexity'))
        allowed.add('usage_scope')
        allowed.update({'candidate_policy_version', 'policy_mode', 'work_class', 'risk_active',
                        'legacy_uncertain', 'risk_basis', 'failure_class', 'candidate_status', 'engine_comparison_id'})
        allowed.add('engine_provider_cost_usd')
        allowed.update('usage_baseline_' + k for k in ('inputTokens','outputTokens','cachedInputTokens'))
        allowed.update('native_total_' + k for k in ('inputTokens','outputTokens','cachedInputTokens'))
        record = {"schema": 3, "product_version": BUILD[0], "build_id": BUILD[1], "router_build_id": ROUTER_BUILD,
                  'runtime_instance': self.runtime_instance, 'execution_platform': sys.platform,
                  "routing_policy_version": POLICY_VERSION, "model_catalog_version": CATALOG_VERSION, "time": time.time(), "time_iso":
                  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event,
                  "session": str(os.getpid())}
        record.update({key: value for key, value in fields.items() if key in allowed and value is not None})
        row = self.threads.get(fields.get('thread'), {})
        if row.get('decision_id') == fields.get('decision_id') and row.get('routing_policy_version') == candidate_policy.VERSION:
            record['routing_policy_version'] = candidate_policy.VERSION
        try:
            private_directory(self.state_dir)
            history = self.state_dir / "history.jsonl"
            append_record(self.state_dir, record)
            self.history_writes += 1
            if self.history_writes % 100 == 0 and history.stat().st_size > 5 * 1024 * 1024:
                self.prune_history(history)
        except OSError:
            pass

    def prune_history(self, history):
        try:
            days = int(read_config(self.config_path).get("history_days", 90))
            compact_history(self.state_dir, days)
        except (OSError, ValueError, KeyError):
            pass

    def record_prompt(self, config, decision_id, tid, prompt, **fields):
        """Persist exact user text only under the owner's explicit local opt-in."""
        if config.get("prompt_logging") is not True or tid in self.temporary_threads:
            return
        if not isinstance(prompt, str) or not prompt.strip():
            return
        allowed = {"model", "effort", "previous_model", "source", "model_reason", "effort_reason",
                   "agent_category", "agent_confidence", "routing_engine", "engine_model", "engine_status",
                   "engine_applied", "continuity_strategy", "request_kind", "quality_floor", "quality_ceiling",
                   "max_effort_allowed", "task_floor", "min_effort", "has_attachments", "task_mode"}
        record = {"schema": 1, "product_version": BUILD[0], "build_id": BUILD[1],
                  "router_build_id": ROUTER_BUILD, "routing_policy_version": POLICY_VERSION,
                  "time": time.time(), "time_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "session": str(os.getpid()), "decision_id": decision_id, "thread": tid,
                  "prompt": prompt}
        record.update({key: value for key, value in fields.items() if key in allowed and value is not None})
        try:
            append_prompt_record(self.state_dir, record)
            self.prompt_writes += 1
            self.maintain_retention(config)
        except (OSError, ValueError, TypeError):
            pass

    def maintain_retention(self, config=None, now=None):
        """Enforce configured retention hourly, including quiet/small datasets."""
        now = time.time() if now is None else now
        if now < self.next_retention_check:
            return
        self.next_retention_check = now + 3600
        config = self.phase_config() if config is None else config
        try:
            history_days = max(0, int(config.get("history_days", 90)))
            prompt_days = max(0, int(config.get("prompt_history_days", history_days)))
            if (self.state_dir / "history.jsonl").exists():
                compact_history(self.state_dir, history_days, now=now)
            if (self.state_dir / "prompts.jsonl").exists():
                compact_prompt_history(self.state_dir, prompt_days, now=now)
        except (OSError, ValueError, TypeError):
            self.next_retention_check = now + 60

    def new_decision(self, tid, model, effort, model_reason, effort_reason, source, previous_model=None, signal=None,
                     agent_category=None, agent_confidence=None, continuity_strategy=None, routing_policy=None):
        previous_decision = self.current_decisions.get(tid)
        if previous_decision and signal == "retry":
            self.record_history("decision_signal", decision_id=previous_decision, thread=tid, signal="retry")
        elif previous_decision and source == "explicit" and previous_model != model:
            self.record_history("decision_signal", decision_id=previous_decision, thread=tid, signal="manual_override")
        decision_id = uuid.uuid4().hex
        title = self.threads.get(tid, {}).get("name") or (tid[:8] if tid else "Sin título")
        self.current_decisions[tid] = decision_id
        if agent_category:
            self.thread_categories.setdefault(tid, {}).update(agent_category=agent_category,
                                                             agent_confidence=agent_confidence or "baja")
        row = self.threads.setdefault(tid, {})
        clear_error(row)
        if model != row.get('model'):
            row.pop('context_window', None)
        self.native_errors.pop(tid, None)
        for field in ("tokens", "observed_model", "observed_effort", "inference_source", "evidence_confidence",
                      "accepted_model", "accepted_effort", "completed_at", "turn_id", "phase_id", "phase_accepted_at",
                      'expected_model','expected_effort','inference_model_mismatch','inference_effort_mismatch'):
            row.pop(field, None)
        row["decision_started_at"] = time.time()
        self.save_task(tid, {"agent_category": agent_category,
                             "agent_confidence": agent_confidence, **row})
        self.record_history("decision_created", decision_id=decision_id, thread=tid, title=title,
                            model=model, effort=effort, previous_model=previous_model,
                            model_reason=model_reason, effort_reason=effort_reason, source=source,
                            agent_category=agent_category, agent_confidence=agent_confidence, status="pending",
                            task_mode="manual" if source == "manual" else "agent" if source == "agent" else "automatic",
                            continuity_strategy=continuity_strategy, **(routing_policy or {}))
        return decision_id

    def log(self, event):
        # The small diagnostic file never contains prompt text, input, auth, paths
        # from messages, tool arguments, or model output.
        event = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event}
        self.events.append(event)
        self.events = self.events[-100:]
        try:
            private_directory(self.state_dir)
            target = self.state_dir / ("status-%s.json" % os.getpid())
            atomic_json(target, {"version": 3, "storage_schema": 3, "product_version": BUILD[0], "build_id": BUILD[1], "router_build_id": ROUTER_BUILD,
                                       "routing_policy_version": POLICY_VERSION, "pid": os.getpid(), "events": self.events,
                                       "heartbeat": time.time(), "threads": self.inventory.visible(self.threads),
                                       "agent_threads": self.inventory.agents(self.threads),
                                       "client_name": self.client_name, "handshake_complete": self.handshake_complete,
                                       "inventory_synced_at": self.inventory.synced_at,
                                       "catalog": {m: sorted(e) for m, e in self.catalog.items()},
                                       "stats": self.stats,
                                       "account_usage": self.account_usage.snapshot,
                                       "telemetry": self.telemetry.snapshot() if self.telemetry else {"enabled": False}})
        except OSError:
            pass  # Diagnostics must never break a user's message.

    def observe_inference(self, record):
        """Associate a completed local OTel event only when it is unambiguous."""
        completion = record.get("event_kind") == "response.completed"
        model, effort = record.get("model"), record.get("effort")
        if not model:
            with self.lock:
                self.stats['telemetry_missing_model'] += 1
            return
        metric_names = ("inference_input_tokens", "inference_output_tokens", "inference_cached_tokens",
                        "inference_cache_write_tokens", "inference_reasoning_tokens", "inference_tool_tokens",
                        "inference_duration_ms", "inference_ttft_ms", "inference_attempt",
                        "inference_http_status", "inference_success")
        metrics = {name: record[name] for name in metric_names if name in record}
        with self.lock:
            now = time.time()
            self.stats['telemetry_records'] += 1
            event_id = record.get("event_id")
            if event_id and event_id in self.inference_ids:
                self.stats['telemetry_duplicates'] += 1
                return
            if event_id:
                self.inference_ids.add(event_id)
                if len(self.inference_ids) > 8192:
                    self.inference_ids = {event_id}
            if completion:
                self.stats["telemetry_events"] += 1
                for field in COMPLETION_FIELDS:
                    if record.get(field) is None or record.get(field) == '':
                        self.stats['telemetry_completion_missing_' + field] += 1
            for field in ('thread_id', 'turn_id', 'timestamp'):
                if record.get(field) is None or record.get(field) == '':
                    self.stats['telemetry_missing_' + field] += 1
            candidate, confirmed, rejection = attribute(record, self.threads, now)
            if candidate is None:
                self.stats['telemetry_' + rejection] += 1
                if completion:
                    self.stats["telemetry_unattributed"] += 1
                    self.stats['telemetry_completion_' + rejection] += 1
                    self.log({"event": "inference_unattributed", "model": model, "effort": effort, 'reason': rejection})
                return
            tid, row = candidate
            expected_model = row.get('phase_model') or row.get('accepted_model') or row.get('model')
            expected_effort = row.get('phase_effort') or row.get('accepted_effort') or row.get('effort')
            mismatch = {'expected_model': expected_model, 'expected_effort': expected_effort,
                        'inference_model_mismatch': model != expected_model,
                        'inference_effort_mismatch': bool(effort and expected_effort and effort != expected_effort)}
            if confirmed:
                self.stats['telemetry_model_mismatch'] += int(mismatch['inference_model_mismatch'])
                self.stats['telemetry_effort_mismatch'] += int(mismatch['inference_effort_mismatch'])
            metrics.update(inference_event_name=record.get("event_name"),
                           inference_timestamp_source=record.get("timestamp_source"),
                           inference_event_kind=record.get("event_kind"), inference_event_id=event_id,
                           phase_id=row.get("phase_id"))
            if not completion:
                key = (tid, self.current_decisions.get(tid), row.get('phase_id'), record.get('event_name'), record.get('event_kind'), model, effort)
                bucket = self.metric_buckets.setdefault(key, {'count': 0, 'failures': 0, 'flushed_at': now - 30})
                bucket['count'] += 1
                bucket['failures'] += int(record.get('event_kind') == 'response.failed' or record.get('inference_http_status', 0) >= 400)
                bucket['fields'] = dict(decision_id=self.current_decisions.get(tid), thread=tid, turn_id=row.get('turn_id'), phase_name=row.get('phase_name'),
                    evidence_confidence='correlated' if confirmed else 'probable',
                    observed_candidate_model=model, observed_candidate_effort=effort, **mismatch, **metrics)
                self.flush_metrics(now=now)
                return
            if not confirmed:
                # A model match is useful health evidence, never proof of the
                # inference used by this decision. Do not populate observed_*.
                self.stats["telemetry_probable"] = self.stats.get("telemetry_probable", 0) + 1
                self.record_history("inference_probable", decision_id=self.current_decisions.get(tid),
                                    thread=tid, turn_id=row.get("turn_id"), evidence_confidence="probable", inference_source="otlp_loopback",
                                    phase_name=row.get('phase_name'),
                                    observed_candidate_model=model, observed_candidate_effort=effort,
                                    **metrics)
                return
            row.update(observed_model=model, observed_effort=effort,
                       inference_source="otlp_loopback", evidence_confidence="confirmed", **mismatch)
            self.stats["telemetry_confirmed"] += 1
            metrics.update(estimate_standard_usage(model, metrics))
            self.record_history("inference_observed", decision_id=self.current_decisions.get(tid), thread=tid,
                                turn_id=row.get('turn_id'), **mismatch,
                                title=row.get("name"), status=row.get("status"), observed_model=model,
                                observed_effort=effort, inference_source="otlp_loopback",
                                evidence_confidence="confirmed",
                                phase_status=row.get("phase_status"), phase_name=row.get("phase_name"),
                                phase_pipeline=row.get("phase_pipeline"), pipeline_mode="observation", **metrics)
            self.log({"event": "inference_observed", "thread": tid, "model": model, "effort": effort})

    def flush_metrics(self, thread=None, now=None):
        """Persist bounded class samples, not a row for every stream packet."""
        now = time.time() if now is None else now
        for key, bucket in list(self.metric_buckets.items()):
            if thread is not None and key[0] != thread:
                continue
            if bucket['count'] and (thread is not None or now - bucket['flushed_at'] >= 30):
                self.record_history('inference_metric', **bucket['fields'],
                                    inference_sample_count=bucket['count'], inference_failure_count=bucket['failures'])
                bucket.update(count=0, failures=0, flushed_at=now)
            if thread is not None:
                self.metric_buckets.pop(key, None)
            elif not bucket['count'] and now - bucket['flushed_at'] >= 60:
                self.metric_buckets.pop(key, None)

    def server_line(self, raw):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                return
            with self.lock:
                if self.account_usage.consume(message):
                    return False
                phase_config = self.phase_config() if message.get("method") == "item/tool/call" else {}
                if self.phases.consume(message, phase_config):
                    return False
                owned, next_page = self.inventory.consume(message)
                if owned:
                    if next_page:
                        self.outbound.append(next_page)
                    else:
                        for tid, name in self.inventory.names.items():
                            if tid in self.threads:
                                self.threads[tid]["name"] = name
                    return False
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
                    if method == "initialize" and "error" not in message:
                        # Some Desktop builds do not expose the follow-up
                        # `initialized` notification through this bridge. The
                        # successful handshake response is authoritative.
                        self.inventory.ready = True
                        self.handshake_complete = True
                    elif method == "model/list" and "error" not in message:
                        for model in result.get("data", []):
                            if model.get("hidden"):
                                continue
                            self.catalog[model["model"]] = {
                                e["reasoningEffort"] for e in model.get("supportedReasoningEfforts", [])}
                    elif method in ("thread/start", "thread/fork", "thread/resume", "thread/read"):
                        thread = result.get("thread") or {}
                        tid = thread.get("id")
                        if tid:
                            if method == 'thread/start' and tid not in self.threads:
                                self.threads[tid] = {'native_total_usage': {'inputTokens':0,'outputTokens':0,'cachedInputTokens':0}}
                            old = {**self.thread_categories.get(tid, {}), **self.threads.get(tid, {})}
                            metadata = thread_metadata(thread, old, params, method)
                            if metadata["side_chat"]:
                                self.temporary_threads.add(tid)
                            self.threads[tid] = {**old,
                                "provider": result.get("modelProvider", thread.get("modelProvider", old.get("provider"))),
                                "model": old.get("model") if old.get("confirmation") == "Aceptado por Codex" else result.get("model", thread.get("model", old.get("model"))),
                                "name": thread.get("name") or thread.get("agentNickname") or old.get("name") or tid[:8],
                                **metadata,
                                "effort": old.get("effort") if old.get("confirmation") == "Aceptado por Codex" else result.get("reasoningEffort") or thread.get("reasoningEffort") or old.get("effort"),
                                "status": thread.get("status", {}).get("type", "unknown"),
                                "confirmation": old.get("confirmation", "Configurado; sin envío observado"),
                                "seen_turn": old.get("seen_turn", method not in ("thread/start", "thread/fork"))}
                            if thread.get("status", {}).get("type") == "active":
                                self.active.add(tid)
                    elif method == "turn/start":
                        tid = params.get("threadId")
                        self.pending.discard(tid)
                        sync = self.sync_after_ack.pop(message.get("id"), None)
                        accepted = self.accepted_routes.pop(message.get("id"), None)
                        if "error" in message:
                            row = self.threads.setdefault(tid, {})
                            diagnostic = rpc_error(message.get("error"))
                            row.update({**(accepted or {}), "status": "error", "confirmation": "Rechazado",
                                        **diagnostic,
                                        **phase_update(row, "blocked", transition=(accepted or {}).get("phase_transition"))})
                            self.log({"event": "turn_rejected", "thread": tid})
                            if accepted:
                                self.record_history("decision_rejected", decision_id=accepted.get("decision_id"),
                                                    thread=tid, status="error", **diagnostic, phase_status="blocked",
                                                    phase_transition=accepted.get("phase_transition"))
                        elif accepted:
                            row = self.threads.setdefault(tid, {})
                            consumed = accepted.pop("consume_pending_phase", None)
                            if consumed and consumed == row.get("pending_phase_id", "legacy"):
                                self.clear_pending_phase(tid)
                            row.update({**accepted, "confirmation": "Aceptado por Codex", "status": "inProgress",
                                        "updated": time.time(),
                                        "turn_id": (result.get("turn") or {}).get("id") or row.get("turn_id"),
                                        "accepted_model": accepted.get("model"), "accepted_effort": accepted.get("effort"),
                                        **phase_update(row, "accepted", model=accepted.get("model"), effort=accepted.get("effort"))})
                            self.phases.begin(tid, row.get("turn_id"), accepted)
                            self.stats["accepted"] += 1
                            if accepted["model"] in MODELS and MODELS[accepted["model"]][1] != "astra":
                                self.stats["non_astra"] += 1
                            self.log({"event": "turn_accepted", "thread": tid, **accepted})
                            self.record_history("decision_accepted", decision_id=accepted.get("decision_id"),
                                                thread=tid, title=self.threads.get(tid, {}).get("name"),
                                                model=accepted.get("model"), effort=accepted.get("effort"),
                                                status="inProgress", phase_status="accepted",
                                                phase_name=accepted.get("phase_name", "execution"),
                                                phase_model=accepted.get("model"), phase_effort=accepted.get("effort"),
                                                phase_transition=accepted.get("phase_transition"),
                                                accepted_model=accepted.get("model"), accepted_effort=accepted.get("effort"),
                                                pipeline_mode="observation", phase_pipeline=row.get("phase_pipeline"))
                        if "error" not in message and sync:
                            # After acknowledgement, turn/start has already applied
                            # the user's mode and permissions. Ask the native server
                            # to publish its actual settings to the Desktop picker.
                            rid = "personal-router-" + uuid.uuid4().hex
                            self.internal_requests.add(rid)
                            self.outbound.append({"id": rid, "method": "thread/settings/update", "params": sync})
                method = message.get("method")
                params = message.get("params") or {}
                self.inventory.notification(method, params)
                tid = params.get("threadId")
                if method == "thread/closed":
                    self.phases.end(tid)
                if method == "turn/started":
                    self.active.add(tid)
                    row = self.threads.setdefault(tid, {})
                    if row.get("turn_id") != (params.get("turn") or {}).get("id"):
                        row.pop("live_plan", None)
                    row.update(status="inProgress", turn_id=(params.get("turn") or {}).get("id"), updated=time.time(), **phase_update(row, "active"))
                    self.record_history("phase_started", decision_id=self.current_decisions.get(tid), thread=tid,
                                        **phase_update(row, "active"))
                elif method == "turn/plan/updated":
                    row = self.threads.get(tid)
                    plan = native_plan(params)
                    if (row is not None and plan is not None and plan["turn_id"] == row.get("turn_id")
                            and row.get("status") in ("active", "inProgress", "running", "waiting")):
                        row["live_plan"] = plan
                        row["updated"] = time.time()
                        self.log({"event": "native_plan_updated", "thread": tid})
                elif method == "error":
                    row = self.threads.get(tid, {})
                    turn_id = params.get("turnId")
                    # Retries are incidents, not completed decisions. Late errors
                    # must never be attached to a newer turn on the same task.
                    if (turn_id and turn_id == row.get("turn_id") and
                            self.current_decisions.get(tid) and not row.get("completed_at")):
                        diagnostic = native_error(params.get("error"))
                        retry = params.get("willRetry")
                        if retry is False:
                            self.native_errors[tid] = (turn_id, diagnostic)
                        else:
                            self.native_errors.pop(tid, None)
                        self.record_history("native_turn_error", decision_id=self.current_decisions[tid],
                                            thread=tid, turn_id=turn_id, **diagnostic,
                                            will_retry=retry if type(retry) is bool else None)
                elif method == "turn/completed":
                    row = self.threads.setdefault(tid, {})
                    turn = params.get("turn") or {}
                    turn_id = turn.get("id")
                    self.commands.finish_turn(tid, turn_id)
                    if turn_id and self.current_decisions.get(tid) and turn_id != row.get("turn_id"):
                        return True  # Forward unchanged, but do not alter current evidence.
                    self.flush_metrics(thread=tid)
                    self.phases.end(tid)
                    self.active.discard(tid)
                    self.pending.discard(tid)
                    status = turn.get("status", "completed")
                    if status == "interrupted":
                        self.clear_pending_phase(tid)
                    pending_error = self.native_errors.pop(tid, None)
                    clear_error(row)
                    diagnostic = {}
                    if status == "failed":
                        diagnostic = native_error(turn.get("error"))
                        if (diagnostic["error_type"] == "unknown" and pending_error and
                                pending_error[0] == turn_id):
                            diagnostic = pending_error[1]
                    phase_status = "completed" if status == "completed" else "failed"
                    row.update(status=status, completed_at=time.time(), updated=time.time(), **diagnostic, **phase_update(row, phase_status))
                    self.log({"event": "turn_completed", "thread": tid})
                    row = self.threads.get(tid, {})
                    tokens = row.get("tokens") or {}
                    self.record_history("decision_completed", decision_id=self.current_decisions.get(tid),
                                        thread=tid, title=row.get("name"), status=row.get("status"), **tokens, **diagnostic,
                                        phase_status=row.get("phase_status"), phase_name=row.get("phase_name"),
                                        phase_model=row.get("phase_model"), phase_effort=row.get("phase_effort"),
                                        phase_transition=row.get("phase_transition"), pipeline_mode="observation",
                                        phase_pipeline=row.get("phase_pipeline"))
                elif method == "thread/closed" and tid in self.temporary_threads:
                    self.active.discard(tid)
                    self.pending.discard(tid)
                    self.current_decisions.pop(tid, None)
                    self.thread_categories.pop(tid, None)
                    self.inventory.hidden.add(tid)
                    self.threads[tid] = {"ephemeral": True, "side_chat": True,
                                         "name": "Chat lateral", "status": "closed"}
                elif method == "thread/name/updated":
                    self.threads.setdefault(tid, {})["name"] = params.get("threadName", params.get("name", tid))
                elif method == "thread/status/changed":
                    status = params.get("status", {}).get("type", "unknown")
                    self.threads.setdefault(tid, {}).update(status=status, updated=time.time())
                    if status in ("error", "failed", "interrupted"):
                        self.phases.end(tid)
                        row = self.threads.get(tid, {})
                        row.update(**phase_update(row, "failed"))
                        self.record_history("decision_error", decision_id=self.current_decisions.get(tid),
                                            thread=tid, title=self.threads.get(tid, {}).get("name"),
                                            status=status, **({k: row[k] for k in DIAGNOSTIC_FIELDS if k in row}
                                                              if row.get("error_type") else {"error_type": "thread_" + status}),
                                            phase_status="failed", phase_name=row.get("phase_name", "execution"),
                                            phase_model=row.get("phase_model"), phase_effort=row.get("phase_effort"),
                                            phase_transition=row.get("phase_transition"))
                elif method == "thread/started":
                    thread = params.get("thread", {})
                    if thread.get("id"):
                        row = self.threads.setdefault(thread["id"], {})
                        metadata = thread_metadata(thread, row)
                        if metadata["side_chat"]:
                            self.temporary_threads.add(thread["id"])
                        row.update(name=thread.get("name") or thread.get("agentNickname") or row.get("name") or thread["id"][:8],
                                   **metadata, updated=time.time())
                        if thread.get("model"):
                            row.setdefault("model", thread["model"])
                            row.setdefault("effort", thread.get("reasoningEffort"))
                            row.setdefault("confirmation", "Configurado; sin envío observado")
                elif method in ("item/started", "item/completed"):
                    item = params.get("item", {})
                    if tid and item.get('type') == 'contextCompaction':
                        self.threads.setdefault(tid, {})
                    if item.get("type") == "commandExecution":
                        turn_id = params.get("turnId") or self.threads.get(tid, {}).get("turn_id")
                        item_id = item.get("id")
                        if method == "item/started":
                            self.stop_commands(self.commands.register(
                                tid, turn_id, item_id, item.get("processId")))
                        else:
                            self.commands.finish_item(tid, turn_id, item_id)
                    if method == "item/completed" and item.get("type") in ("agentMessage", "assistantMessage", "message"):
                        text = item.get("text") or item.get("content") or ""
                        if isinstance(text, list):
                            text = "\n".join(part.get("text", "") for part in text if isinstance(part, dict))
                        if isinstance(text, str):
                            context = summarize_response_context(text)
                            if context:
                                # A progress item can report completion of a
                                # substep without closing the whole task.
                                if (item.get("phase") or item.get("channel")) in ("commentary", "analysis"):
                                    context["completed"] = False
                                    context["response_kind"] = "progress"
                                row = self.threads.setdefault(tid, {})
                                row["response_context"] = context
                                contract = merge_contract(row.get("task_contract") or {"floor": row.get("task_floor")}, context)
                                row["task_contract"] = contract
                                row["task_floor"] = contract.get("floor") if contract.get("status") == "pending" else None
                                if context.get("completed"):
                                    self.clear_pending_phase(tid)
                                self.save_task(tid, row)
                                self.record_history("task_context", thread=tid, title=row.get("name"),
                                                    task_floor=row.get("task_floor") or "cleared")
                                if context.get("has_plan") and context.get("plan_steps"):
                                    planned = proposed_phase(row.get("model"), row.get("model"), row.get("effort"),
                                                             row.get("agent_category"), context["plan_steps"])
                                    row["phase_pipeline"] = planned["phase_pipeline"]
                                    row.update(**phase_update(row, row.get("phase_status", "active")))
                                    self.record_history("phase_plan_updated", thread=tid, decision_id=self.current_decisions.get(tid),
                                                        phase_pipeline=row["phase_pipeline"], pipeline_mode="plan_and_observation")
                                row["updated"] = time.time()
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
                    self.threads.setdefault(tid, {}).update(tokens=tokens, updated=time.time(),
                        context_window=context_window(params.get('tokenUsage')))
                    if self.current_decisions.get(tid):
                        self.record_history("decision_usage", decision_id=self.current_decisions[tid], thread=tid,
                                            turn_id=self.threads[tid].get('turn_id'), usage_scope='last_native_update', **tokens)
                    total = params.get('tokenUsage', {}).get('total')
                    if isinstance(total, dict):
                        self.threads[tid]['native_total_usage'] = {k:total[k] for k in ('inputTokens','outputTokens','cachedInputTokens') if k in total}
                        if self.current_decisions.get(tid):
                            self.record_history('decision_usage_total', decision_id=self.current_decisions[tid], thread=tid,
                                turn_id=self.threads[tid].get('turn_id'), usage_scope='thread_total_snapshot',
                                **{'native_total_'+k:v for k,v in self.threads[tid]['native_total_usage'].items()})
                elif method == "thread/settings/updated":
                    settings = params.get("threadSettings") or {}
                    state = self.threads.setdefault(tid, {})
                    if settings.get("model"):
                        if settings['model'] != state.get('configured_model', state.get('model')):
                            state.pop('context_window', None)
                        state["configured_model"] = settings["model"]
                        state["configured_effort"] = settings.get("effort")
                        # Published picker settings can arrive after start/completion,
                        # and may already describe the next turn. Keep lifecycle intact.
                        if not state.get("confirmation") == "Aceptado por Codex":
                            state.update(model=settings["model"], effort=settings.get("effort"))
                        self.log({"event": "native_settings", "thread": tid,
                                  "model": settings["model"], "effort": settings.get("effort")})
                        self.record_history("phase_settings_published", decision_id=self.current_decisions.get(tid),
                                            thread=tid, title=state.get("name"), status=state.get("status"),
                                            phase_status=state.get("phase_status"), phase_name=state.get("phase_name", "execution"),
                                            phase_transition=state.get("phase_transition"), configured_model=settings["model"],
                                            configured_effort=settings.get("effort"), pipeline_mode="observation",
                                            phase_pipeline=state.get("phase_pipeline"))
                if tid and tid in self.threads:
                    row = self.threads[tid]
                    before = (row.get('context_compaction') or {}).get('state')
                    update_context_compaction(row, method, params)
                    after = (row.get('context_compaction') or {}).get('state')
                    if before != after:
                        self.log({'event': 'context_compaction', 'thread': tid, 'state': after or 'cleared'})
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
        return True

    def drain_outbound(self):
        self.maintain_retention()
        with self.lock:
            request = self.account_usage.poll(self.handshake_complete and self.client_name != 'other')
            if request:
                self.outbound.append(request)
            self.flush_metrics()
            self.phases.poll()
            result, self.outbound = self.outbound, []
            return result

    def client_line(self, raw, mode_at_submission=None):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                return raw
            method = message.get("method")
            params = message.get("params") or {}
            if not isinstance(params, dict):
                return raw
            with self.lock:
                if method == "thread/start":
                    prepared = self.phases.prepare(message, self.phase_config())
                    if prepared is not message:
                        message = prepared
                        params = message["params"]
                        raw = (json.dumps(message, ensure_ascii=False) + "\n").encode()
                if method in ("turn/interrupt", "turn/steer", "thread/settings/update", "turn/settings/update"):
                    self.phases.disable_turn(params.get("threadId"))
                if method == "turn/interrupt":
                    self.stop_commands(self.commands.interrupt(
                        params.get("threadId"), params.get("turnId")))
                if method == "initialize":
                    self.phases.api_enabled = (params.get("capabilities") or {}).get("experimentalApi") is True
                    name = (params.get("clientInfo") or {}).get("name", "unknown")
                    self.client_name = name if name in ("codex_desktop", "codex_app", "Codex Desktop") else "other"
                if method == "initialized":
                    self.inventory.ready = True
                if "id" in message and method in (
                        "initialize", "model/list", "thread/start", "thread/fork", "thread/resume", "thread/read", "turn/start"):
                    self.requests[message["id"]] = (method, params)
                if method != "turn/start":
                    return raw
                tid = params.get("threadId")
                state = self.threads.get(tid, {})
                if state.get("ephemeral") and not (state.get("parent") or state.get("side_chat")):
                    # Internal in-memory roots (for example automatic title
                    # helpers) are not user tasks and must keep Codex's native
                    # cheap configuration. Do not create decision telemetry.
                    self.log({"event": "preserved", "reason": "internal_ephemeral", "thread": tid})
                    return raw
                if tid in self.active or tid in self.pending:
                    self.log({"event": "preserved", "reason": "active_turn", "thread": tid})
                    return raw
                self.pending.add(tid)
                mode_at_submission = mode_at_submission or read_mode(self.state_dir, tid)
            routed = self.route_turn(message, raw, mode_at_submission)
            with self.lock:
                if routed == raw and "id" in message and message["id"] not in self.accepted_routes:
                    self.observe_preserved(message, mode_at_submission)
                return routed
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as error:
            with self.lock:
                self.log({"event": "preserved", "reason": "router_error"})
                self.record_history("router_error", error_type=type(error).__name__, status="error")
            return raw

    def observe_preserved(self, message, mode_at_submission=None):
        """Observe explicit settings even while paused; never label them routed."""
        params = message["params"]
        row = self.threads.get(params.get("threadId"), {})
        settings = (params.get("collaborationMode") or {}).get("settings") or {}
        model = settings.get("model") or params.get("model") or row.get("configured_model") or row.get("model")
        effort = settings.get("reasoning_effort") or params.get("effort") or row.get("configured_effort") or row.get("effort")
        if model:
            tid = params.get("threadId")
            items = params.get("input") if isinstance(params.get("input"), list) else []
            text = user_text(items)
            if cancels_work(text):
                self.clear_pending_phase(tid)
            category, confidence = classify_agent_identity(text, row.get("name", ""), has_attachments(items),
                                                           previous=row.get("agent_category"))
            manual = (mode_at_submission or read_mode(self.state_dir, params.get("threadId"))) == "manual"
            model_reason = "modo manual de esta tarea; se respeta el modelo elegido en Codex" if manual else "configuración original; sin intervención del selector"
            effort_reason = "nivel configurado manualmente en Codex"
            source = "manual" if manual else "preserved"
            decision_id = self.new_decision(tid, model, effort, model_reason, effort_reason, source,
                                            row.get("model"), agent_category=category, agent_confidence=confidence)
            self.record_prompt(self.phase_config(), decision_id, tid, text, model=model, effort=effort,
                               previous_model=row.get("model"), source=source, model_reason=model_reason,
                               effort_reason=effort_reason, agent_category=category, agent_confidence=confidence,
                               has_attachments=has_attachments(items), task_mode="manual" if manual else "automatic")
            self.accepted_routes[message["id"]] = {"model": model, "effort": effort, "reason": model_reason,
                "model_reason": model_reason, "effort_reason": effort_reason, "source": source,
                "agent_category": category, "agent_confidence": confidence, "decision_id": decision_id}
            if row.get('pending_phase_floor') and resumes_work(text):
                self.accepted_routes[message['id']]['consume_pending_phase'] = row.get('pending_phase_id', 'legacy')

    def cancel_prepared(self, message):
        with self.lock:
            tid, request = message["params"].get("threadId"), message.get("id")
            self.pending.discard(tid)
            self.requests.pop(request, None)
            self.accepted_routes.pop(request, None)
            self.sync_after_ack.pop(request, None)
            row = self.threads.get(tid, {})
            row.update(status="interrupted", completed_at=time.time(), **phase_update(row, "failed"))
            self.record_history("decision_completed", decision_id=self.current_decisions.get(tid), thread=tid, status="interrupted")

    def classify_external(self, config, state, candidates):
        self.lock.release()
        try:
            return run_jev(config, self.state_dir, state, candidates)
        finally:
            self.lock.acquire()

    def route_turn(self, message, raw, mode_at_submission=None):
        with self.lock:
            return self._route_turn_locked(message, raw, mode_at_submission)

    def _route_turn_locked(self, message, raw, mode_at_submission=None):
        params = message["params"]
        tid = params.get("threadId")
        if (mode_at_submission or read_mode(self.state_dir, tid)) == "manual":
            self.log({"event": "preserved", "thread": tid, "reason": "task_manual"})
            return raw
        config = read_config(self.config_path)
        if not config.get("enabled", False):
            self.log({"event": "preserved", "thread": tid, "reason": "disabled"})
            return raw
        state = self.threads.get(tid, {})
        mode = params.get("collaborationMode") or {}
        settings = mode.get("settings") or {}
        current = settings.get("model") or params.get("model") or state.get("model")
        routes = available_routes(config.get("routes", DEFAULT_ROUTES), self.catalog)
        owned_models = set(MODELS) | {r["model"] for r in routes.values()}
        # Do not move a non-OpenAI conversation to paid ChatGPT implicitly.
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
        if cancels_work(text):
            self.clear_pending_phase(tid)
        previous = state.get("tier")
        if previous is None:
            previous = MODELS.get(current, (None, None, None))[2]
            # A fresh thread's default Astra isn't evidence of a complex task.
            if not state.get("seen_turn"):
                previous = None
        response_context = effective_context(state)
        route, reasons = select_route_details(text, routes, previous, state.get("effort"), has_attachments(items), response_context)
        if reasons.get("new_task"):
            state.pop("task_floor", None)
            state.pop("response_context", None)
            state.pop("task_contract", None)
            state.pop("candidate_contract", None)
            state.pop("pending_phase_floor", None)
            state.pop("pending_phase_name", None)
            self.clear_pending_phase(tid)
            for key in ("task_floor", "task_contract"):
                self.thread_categories.get(tid, {}).pop(key, None)
            self.save_task(tid, state)
            self.record_history("task_context", thread=tid, title=state.get("name"), task_floor="cleared")
        pending_phase_floor = state.get("pending_phase_floor")
        resumes_boundary = (pending_phase_floor in TIERS and not reasons.get("new_task") and resumes_work(text))
        if resumes_boundary and reasons.get("source") == "automatic":
            route = dict(routes[pending_phase_floor])
            reasons.update(quality_floor=pending_phase_floor, quality_ceiling=pending_phase_floor,
                           min_effort=route["effort"], max_effort_allowed=False,
                           model="continuación autorizada de una fase que requiere cambiar de modelo en un turno nuevo",
                           effort="mínimo de razonamiento de la fase pendiente", request_kind="phase_continuation")
        baseline_route, baseline_reasons = dict(route), dict(reasons)
        if (reasons.get("quality_floor") in ("normal", "complex", "critical") and
                reasons.get("source") == "automatic" and reasons.get("request_kind") in ("task", "project_review")):
            contract = merge_contract(state.get("task_contract"), {
                "implementation_pending": True, "work_floor": reasons["quality_floor"],
                "plan_steps": plan_steps(text), "awaiting_approval": False,
                "response_kind": "progress", "contract_version": 2})
            state["task_contract"], state["task_floor"] = contract, contract.get("floor")
            self.save_task(tid, state)
        steps = plan_steps(text) or (state.get("task_contract") or {}).get("plan_steps")
        category, confidence = classify_agent_identity(text, state.get("name", ""), has_attachments(items),
                                                       baseline_reasons["model"], state.get("agent_category"))
        engine_name = config.get("routing_engine", ENGINE_RULES)
        if engine_name not in ENGINES:
            engine_name = ENGINE_RULES
        # Identity/title and an ambiguous fallback tier are not quality evidence.
        # Only current workload signals or an instruction to resume known work
        # establish a floor. Continuity is independent of the proposed route.
        routing_policy = {key: reasons[key] for key in ("request_kind", "quality_floor", "quality_ceiling", "max_effort_allowed", "min_effort")}
        routing_policy["routing_policy_version"] = POLICY_VERSION
        candidates = candidate_routes(routes, self.catalog, routing_policy)
        assessment = None
        trial_choices = {}
        trial_route = None
        policy_mode = candidate_policy.mode(config)
        if reasons.get('source') == 'automatic' and policy_mode != 'reference':
            from outcome_evaluation import check_feedback
            previous_decision = self.current_decisions.get(tid)
            failed_check = check_feedback(self.state_dir, previous_decision)
            failure = candidate_policy.failure_kind(state, failed_check)
            assessment = candidate_policy.profile(text, attachment_summary(items), response_context,
                                                  state.get('candidate_contract'), failure)
            trial_choices = candidate_policy.candidates(routes, self.catalog, assessment)
            trial_route = candidate_policy.local_route(assessment, trial_choices)
            state['candidate_contract'] = candidate_policy.next_contract(state.get('candidate_contract'), assessment,
                                                                         previous_decision if failed_check else None)
            self.save_task(tid, state)
            if (trial_route and not resumes_boundary and assessment['work_class'] in
                    candidate_policy.enabled_classes(config, self.state_dir, ROUTER_BUILD)):
                route = {k:trial_route[k] for k in ('model', 'effort')}
                reasons.update(tier=trial_route['tier'],
                    model='política 9 verificada para alcance ' + assessment['work_class'],
                    effort='razonamiento suficiente en candidatos compartidos',
                    quality_floor=trial_route['tier'], min_effort=trial_route['effort'])
                baseline_route, baseline_reasons = dict(route), dict(reasons)
                routing_policy.update(candidate_policy_version=candidate_policy.VERSION,
                    routing_policy_version=candidate_policy.VERSION, work_class=assessment['work_class'],
                    risk_active=assessment['risk_active'], quality_floor=trial_route['tier'],
                    min_effort=trial_route['effort'])
                candidates = trial_choices
        external_allowed = reasons.get("source") == "automatic" and bool(candidates)
        if routing_policy.get('candidate_policy_version') and not assessment['requires_jev']:
            external_allowed = False
        state_for_engine = build_state(text, attachment_summary(items), current, state.get("effort"), reasons.get("signal") == "retry")
        state_for_engine.update(routing_policy)
        safe_context = context_for_engine(response_context) if not reasons.get("new_task") else None
        if safe_context and reasons.get("request_kind") not in ("acknowledgement", "status_check", "bounded", "mechanical"):
            state_for_engine["work_context"] = safe_context
            if reasons.get("request_kind") in ("planned_followup", "work_followup", "context_followup", "ambiguous", "retry"):
                state_for_engine["previous_response_context"] = safe_context
        engine_result = {"engine": ENGINE_RULES, "status": "ok", "latency_ms": 0,
                         "route": {"model": route["model"], "effort": route["effort"]}, "engine_model": "local-policy"}
        if external_allowed and engine_name == ENGINE_JEV:
            engine_result = self.classify_external(config, state_for_engine, candidates)
        engine_applied = False
        candidate_jev_allowed = (not routing_policy.get('candidate_policy_version') or
                                 candidate_policy.accepted_jev(engine_result, config.get('jev') or {}))
        if routing_policy.get('candidate_policy_version') and engine_result.get('engine') == ENGINE_JEV and engine_result.get('status') == 'ok' and not candidate_jev_allowed:
            engine_result = dict(engine_result, status='abstained', engine_failure='uncalibrated_confidence')
        if engine_result.get("engine") != ENGINE_RULES and engine_result.get("status") == "ok" and engine_result.get("route") and candidate_jev_allowed:
            proposed = engine_result["route"]
            continuity_strategy = engine_result.get("continuity_strategy")
            chosen_route = {"model": proposed["model"], "effort": proposed["effort"]}
            if any(item["model"] == chosen_route["model"] and item["effort"] == chosen_route["effort"] for item in candidates.values()):
                route = chosen_route
                engine_applied = True
                label = "Jev"
                if engine_name == ENGINE_JEV and continuity_strategy == "continue":
                    reasons["model"] = "Jev continuó la tarea y eligió %s" % proposed.get("label", route["model"])
                    reasons["effort"] = "Jev reevaluó el razonamiento necesario para este seguimiento"
                else:
                    reasons["model"] = "%s reconsideró la petición y eligió %s" % (label, proposed.get("label", route["model"]))
                    reasons["effort"] = "%s propuso este nivel de razonamiento para la complejidad observada" % label
            else:
                engine_result["status"] = "guardrail"
                engine_result["engine_failure"] = "route_outside_policy"
                reasons["model"] = "Jev propuso una combinación fuera de los límites de la petición; " + baseline_reasons["model"]
                reasons["effort"] = "respaldo local: " + baseline_reasons["effort"]
        elif engine_name != ENGINE_RULES and external_allowed:
            label = "Jev"
            failure = {"invalid": "respondió sin una elección única válida",
                       "not_configured": "no está configurado"}.get(engine_result.get("status"), "no estuvo disponible")
            reasons["model"] = "%s %s; se aplicó la política local: %s" % (label, failure, baseline_reasons["model"])
            reasons["effort"] = "respaldo local: " + baseline_reasons["effort"]
        # The configured engine may have been attempted, but local policy owns
        # the final selection after a malformed response, failure or guardrail.
        effective_engine = engine_result.get("engine", ENGINE_RULES) if engine_applied else ENGINE_RULES
        model, effort = route["model"], route["effort"]
        if effort == "ultra" and model in self.catalog and effort not in self.catalog[model] and "max" in self.catalog[model]:
            effort = "max"
            reasons["effort"] += "; Ultra no está disponible para este modelo, se utiliza Máx."
        if effort not in self.catalog.get(model, set()):
            if reasons.get("source") == "automatic" and candidates:
                alternative = next(iter(candidates.values()))
                model, effort = alternative["model"], alternative["effort"]
                reasons["model"] = "combinación disponible que cumple los mínimos de la tarea"
                reasons["effort"] = "mínimo compatible con el catálogo de esta instalación"
                effective_engine, engine_applied = ENGINE_RULES, False
            else:
                self.log({"event": "preserved", "thread": tid, "reason": "catalog_unavailable"})
                return raw
        changed = copy.deepcopy(message)
        changed["params"]["model"] = model
        changed["params"]["effort"] = effort
        if "collaborationMode" in params and params["collaborationMode"] is not None:
            changed["params"]["collaborationMode"]["settings"]["model"] = model
            changed["params"]["collaborationMode"]["settings"]["reasoning_effort"] = effort
        tier = reasons.get("tier", "complex")
        if engine_applied:
            matched = [r for r in candidates.values() if r["model"] == model and r["effort"] == effort]
            tier = next((r["tier"] for r in matched if r["tier"] == tier), matched[0]["tier"] if matched else tier)
        continuity_strategy = engine_result.get("continuity_strategy") if engine_applied and engine_name == ENGINE_JEV else None
        decision_id = self.new_decision(tid, model, effort, reasons["model"], reasons["effort"], reasons["source"],
                                        current, reasons.get("signal"), category, confidence, continuity_strategy, routing_policy)
        baseline = state.get('native_total_usage')
        if isinstance(baseline, dict):
            self.record_history('decision_usage_baseline', decision_id=decision_id, thread=tid,
                                **{'usage_baseline_'+k:v for k,v in baseline.items()})
        if assessment is not None:
            self.record_policy_comparison(config, decision_id, tid, assessment, trial_route, trial_choices,
                                          model, effort, routing_policy, state_for_engine)
        self.record_prompt(config, decision_id, tid, text, model=model, effort=effort, previous_model=current,
                           source=reasons["source"], model_reason=reasons["model"], effort_reason=reasons["effort"],
                           agent_category=category, agent_confidence=confidence, routing_engine=effective_engine,
                           engine_model=engine_result.get("engine_model"), engine_status=engine_result.get("status"),
                           engine_applied=engine_applied, continuity_strategy=continuity_strategy,
                           has_attachments=has_attachments(items), task_mode="automatic", **routing_policy)
        self.record_engine_comparisons(config, decision_id, tid, candidates, state_for_engine, engine_name,
                                       engine_result, baseline_route, external_allowed)
        self.record_history("decision_routed", decision_id=decision_id, thread=tid, model=model, effort=effort,
                            routing_engine=effective_engine, engine_applied=engine_applied,
                            continuity_strategy=continuity_strategy, **proposed_phase(current, model, effort, category, steps))
        decision = {"model": model, "effort": effort, "reason": reasons["model"],
                    "routing_policy_version": routing_policy['routing_policy_version'],
                    "policy_mode": policy_mode,
                    "quality_floor": routing_policy.get("quality_floor"), "min_effort": routing_policy.get("min_effort"),
                    "quality_ceiling": routing_policy.get("quality_ceiling"),
                    "model_reason": reasons["model"], "effort_reason": reasons["effort"],
                    "source": reasons["source"], "agent_category": category,
                    "agent_confidence": confidence, "decision_id": decision_id,
                    "routing_engine": effective_engine, "engine_model": engine_result.get("engine_model"),
                    "engine_status": engine_result.get("status"), "engine_confidence": engine_result.get("confidence"),
                    "engine_latency_ms": engine_result.get("latency_ms"), "engine_applied": engine_applied,
                    "continuity_strategy": continuity_strategy}
        if resumes_boundary:
            decision["consume_pending_phase"] = state.get("pending_phase_id", "legacy")
        decision.update(proposed_phase(current, model, effort, category, steps))
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

    def record_policy_comparison(self, config, decision_id, tid, assessment, proposed, choices,
                                 selected_model, selected_effort, active_policy, engine_state):
        """Only symbolic metadata; comparison never mutates the active request."""
        fields = {k:assessment[k] for k in ('work_class', 'risk_active', 'legacy_uncertain', 'risk_basis', 'failure_class')}
        self.record_history('policy_comparison', decision_id=decision_id, thread=tid,
            candidate_policy_version=candidate_policy.VERSION, policy_mode=candidate_policy.mode(config),
            candidate_status='applied' if active_policy.get('candidate_policy_version') else 'compared' if proposed else 'unavailable',
            model=selected_model, effort=selected_effort,
            proposed_model=(proposed or {}).get('model'), proposed_effort=(proposed or {}).get('effort'), **fields)
        if (not config.get('candidate_jev_comparison') or not choices or not assessment['requires_jev']
                or active_policy.get('candidate_policy_version')):
            return
        if not SHADOW_SLOTS.acquire(blocking=False):
            self.record_history('policy_comparison_jev', decision_id=decision_id, thread=tid,
                                candidate_policy_version=candidate_policy.VERSION, engine_status='skipped')
            return
        trial_state = dict(engine_state, **assessment)
        def compare():
            try:
                result = run_jev(config, self.state_dir, trial_state, choices)
                chosen = result.get('route') or {}
                self.record_history('policy_comparison_jev', decision_id=decision_id, thread=tid,
                    candidate_policy_version=candidate_policy.VERSION, routing_engine=ENGINE_JEV,
                    engine_active=False, engine_status=result.get('status'), engine_comparison_id=uuid.uuid4().hex,
                    engine_confidence=result.get('confidence'), engine_failure=result.get('engine_failure'),
                    engine_latency_ms=result.get('latency_ms'),
                    engine_provider_cost_usd=result.get('engine_provider_cost_usd'),
                    proposed_model=chosen.get('model'), proposed_effort=chosen.get('effort'),
                    **{k:v for k,v in result.items() if k in ('engine_input_tokens','engine_output_tokens','engine_cached_tokens')})
            finally:
                SHADOW_SLOTS.release()
        threading.Thread(target=compare, daemon=True).start()

    def record_engine_comparisons(self, config, decision_id, tid, candidates, state, active_engine, active_result, baseline_route, allowed):
        """Record comparable, content-free engine choices. Shadow engines never affect Codex."""
        def record(result, active):
            proposed = result.get("route") or {}
            self.record_history("engine_comparison", decision_id=decision_id, thread=tid, routing_engine=result.get("engine", ENGINE_RULES),
                                engine_comparison_id=uuid.uuid4().hex,
                                engine_active=active, engine_model=result.get("engine_model"), engine_status=result.get("status"),
                                engine_confidence=result.get("confidence"), engine_latency_ms=result.get("latency_ms"),
                                engine_failure=result.get("engine_failure"), engine_input_tokens=result.get("engine_input_tokens"),
                                engine_provider_cost_usd=result.get('engine_provider_cost_usd'),
                                engine_output_tokens=result.get("engine_output_tokens"), engine_cached_tokens=result.get("engine_cached_tokens"),
                                proposed_model=proposed.get("model"), proposed_effort=proposed.get("effort"),
                                continuity_strategy=result.get("continuity_strategy"))
        record(active_result, True)
        shadows = config.get("comparison_engines") or []
        seen = {active_result.get("engine", ENGINE_RULES), active_engine}
        if allowed:
            for name in shadows:
                if name not in ENGINES or name in seen:
                    continue
                seen.add(name)
                if name == ENGINE_RULES:
                    record({"engine": ENGINE_RULES, "status": "ok", "latency_ms": 0,
                            "route": baseline_route, "engine_model": "local-policy"}, False)
                elif name == ENGINE_JEV:
                    if SHADOW_SLOTS.acquire(blocking=False):
                        def compare():
                            try:
                                record(run_jev(config, self.state_dir, state, candidates), False)
                            finally:
                                SHADOW_SLOTS.release()
                        threading.Thread(target=compare, daemon=True).start()
                    else:
                        record({"engine": ENGINE_JEV, "status": "skipped", "engine_failure": "busy"}, False)


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
        installation = discover(config) if config.get("installation_mode") == "auto" else None
        binary = installation.backend if installation else backend_path(config)
    except (ValueError, KeyError, TypeError, OSError):
        # Don't expose config or credential-bearing arguments in diagnostics.
        print("Personal router: backend configuration is unavailable.", file=sys.stderr)
        return 1
    args = sys.argv[1:]
    # Other CLI commands, including version/schema, remain the original program.
    is_server = uses_stdio(args)
    env = dict(os.environ)
    env.pop("PERSONAL_CODEX_ROUTER_CONFIG", None)
    env.pop("CODEX_CLI_PATH", None)
    # Desktop removes this identity when it sees a custom executable. Our child
    # is still its original installed engine, so preserve that original identity.
    family = installation.package_family if installation else config.get("windows_sandbox_package_family")
    if family and os.name == "nt":
        env["CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY"] = family
    flags = creation_flags()
    if not is_server:
        if os.name != "nt":
            os.execve(str(binary), [str(binary), *args], env)
        return subprocess.call([str(binary), *args], env=env, creationflags=flags,
                               stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
    router = Router(config_path, os.environ.get("PERSONAL_CODEX_ROUTER_STATE"))
    if router.phases.enabled:
        args = with_server_overrides(args, ["-c", "features.step_model_switching=true"])
    telemetry = None
    if config.get("inference_telemetry", False):
        try:
            telemetry = LocalInferenceTelemetry(router.observe_inference)
            router.set_telemetry(telemetry)
            args = with_loopback_telemetry(args, telemetry.endpoint, telemetry.token, env=env)
        except OSError:
            telemetry = None
    try:
        proc = subprocess.Popen([str(binary), *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, creationflags=flags,
                            start_new_session=os.name != "nt")
    except OSError:
        if telemetry:
            telemetry.close()
        raise
    if os.name != "nt":
        def interrupted(signum, frame):
            stop_backend(proc)
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
    router.log({"event": "bridge_started", "backend_pid": proc.pid,
                "inference_telemetry": bool(telemetry),
                "prompt_logging": config.get("prompt_logging") is True})
    router.confirm_restart_settings(config, bool(telemetry))
    heartbeat_stop = threading.Event()
    write_lock = threading.Lock()
    output_lock = threading.Lock()

    def write_client(data):
        with output_lock:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    def write_native(data):
        with write_lock:
            proc.stdin.write(data)
            proc.stdin.flush()

    def heartbeat_worker():
        while not heartbeat_stop.wait(2):
            with router.lock:
                request = router.inventory.poll(router.threads)
                if request:
                    router.outbound.append(request)
                # Keep liveness fresh without growing the event history.
                previous_events = list(router.events)
                router.log({"event": "heartbeat"})
                router.events = previous_events
            for command in router.drain_outbound():
                try:
                    write_native((json.dumps(command) + "\n").encode())
                except (ValueError, BrokenPipeError, OSError):
                    return
    threading.Thread(target=heartbeat_worker, daemon=True).start()

    dispatcher = Dispatcher(router, write_native, write_client)

    def input_worker():
        try:
            for line in input_lines(sys.stdin.buffer, heartbeat_stop):
                dispatcher.submit(line)
        except (ValueError, BrokenPipeError, OSError):
            pass
        finally:
            dispatcher.close()
            try:
                with write_lock:
                    proc.stdin.close()
            except OSError:
                pass

    input_thread = threading.Thread(target=input_worker, daemon=True)
    input_thread.start()
    stderr_worker = threading.Thread(target=copy_bytes, args=(proc.stderr, sys.stderr.buffer), daemon=True)
    stderr_worker.start()
    try:
        for line in proc.stdout:
            forward = router.server_line(line)
            if forward is not False:
                write_client(line)
            for command in router.drain_outbound():
                try:
                    write_native((json.dumps(command) + "\n").encode())
                except (ValueError, BrokenPipeError, OSError):
                    pass
    except (BrokenPipeError, OSError):
        if proc.poll() is None:
            stop_backend(proc)
    finally:
        heartbeat_stop.set()
        input_thread.join(timeout=1)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            stop_backend(proc)
        stderr_worker.join(timeout=1)
        router.log({"event": "bridge_stopped", "exit_code": proc.returncode})
        if telemetry:
            telemetry.close()
        if proc.returncode:
            router.record_history("bridge_error", status="error", error_type="backend_exit",
                                  error_code=proc.returncode)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
