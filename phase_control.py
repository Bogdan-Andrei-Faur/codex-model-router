"""Opt-in dynamic-tool boundaries; all methods run under the router lock.

No worker waits on native RPC: the held tool call is released by its settings
acknowledgement or heartbeat deadline. Tool arguments never enter persistence.
"""
import copy
import hashlib
import json
import time
import uuid

from phase_tracking import ASTRA, can_switch_within_turn, transition_kind
from routing import DEFAULT_ROUTES, EFFORTS
from state_store import atomic_json
from task_modes import read_mode

TOOL = "router_phase_checkpoint"
TIERS = ("simple", "normal", "complex", "critical")
PHASES = ("investigate", "implement", "verify", "summarize")
SPEC = {"type": "function", "name": TOOL,
    "description": "Mandatory phase boundary for this routed thread. If a turn has two or more substantive phases, you MUST call this tool after completing the current phase and before any reasoning or tool call for the next phase. Typical boundaries are investigate→implement, implement→verify, and verify→summarize. Finish every outstanding tool call first, then await this checkpoint alone; never call it in parallel. Classify only the remaining phase: simple for routine summaries, normal for straightforward implementation or checks, complex for debugging, cross-system analysis, contradictory constraints or adversarial verification, and critical for security or production risk. The router may keep the current model. Do not call before the first phase, after the final phase, for trivial single-phase work, or twice for the same phase. This checkpoint grants no permission: all user instructions, approvals, and safety requirements remain unchanged.",
    "inputSchema": {"type": "object", "properties": {
        "phase": {"type": "string", "enum": list(PHASES)},
        "complexity": {"type": "string", "enum": list(TIERS)}},
        "required": ["phase", "complexity"], "additionalProperties": False}}


class PhaseController:
    def __init__(self, router, enabled=False, clock=time.monotonic):
        self.router, self.enabled, self.clock = router, enabled, clock
        self.api_enabled = False
        self.starts, self.owned, self.turns, self.pending = set(), set(), {}, {}
        self.prefix = "router-phase-" + uuid.uuid4().hex + "-"
        self.sequence = 0

    def marker(self, tid):
        return self.router.state_dir / "phase-threads" / (hashlib.sha256(tid.encode()).hexdigest() + ".json")

    def owns(self, tid):
        if not isinstance(tid, str) or not tid:
            return False
        if tid not in self.owned:
            try:
                if json.loads(self.marker(tid).read_text()).get("thread") == tid:
                    self.owned.add(tid)
            except (OSError, ValueError, AttributeError):
                pass
        return tid in self.owned

    def prepare(self, message, config):
        """Register only new, durable root tasks; never alter existing tools."""
        p = message.get("params") or {}
        existing = p.get("dynamicTools") or []
        if (not self.enabled or not self.api_enabled or not config.get("enabled") or not config.get("phase_routing")
                or message.get("method") != "thread/start" or "id" not in message
                or p.get("ephemeral") or p.get("modelProvider") not in (None, "openai")
                or not isinstance(existing, list)
                or any(not isinstance(t, dict) or t.get("name") == TOOL for t in existing)):
            return message
        changed = copy.deepcopy(message)
        changed["params"]["dynamicTools"] = existing + [copy.deepcopy(SPEC)]
        self.starts.add(message["id"])
        return changed

    def begin(self, tid, turn, decision):
        self.end(tid)
        if self.owns(tid) and turn:
            self.turns[tid] = {"id": turn, "allowed": decision.get("source") == "automatic",
                "floor": decision.get("quality_floor"), "min_effort": decision.get("min_effort"),
                "decision_id": decision.get("decision_id"), "seen": set(), "count": 0}

    def end(self, tid):
        self.turns.pop(tid, None)
        for rid, job in list(self.pending.items()):
            if job["thread"] == tid:
                self.pending.pop(rid)
                self.reply(job["call"], "cancelled")

    def disable_turn(self, tid):
        if tid in self.turns:
            self.turns[tid]["allowed"] = False
        # Keep the current held call until the settings ack or timeout. A sent
        # native update cannot be revoked, and must not race a released tool.

    def reply(self, call, status):
        instruction = ("This phase requires a model that cannot be selected within this turn. Stop this phase and explain that continuation in a new turn is needed. Do not repeat this checkpoint."
            if status == "requires_new_turn" else "Continue the authorized task. Do not repeat this checkpoint.")
        self.router.outbound.append({"id": call, "result": {"success": True,
            "contentItems": [{"type": "inputText", "text": json.dumps({"status": status,
                "instruction": instruction})}]}})

    def record(self, job, status):
        accepted = {"accepted_model": job["model"], "accepted_effort": job["effort"]} if status == "applied" else {}
        self.router.record_history("phase_checkpoint", decision_id=job.get("decision_id"), thread=job["thread"],
            turn_id=job.get("turn_id"),
            phase_id=job.get("phase_id"), phase_source_model=job.get("source_model"),
            phase_name=job["phase"], phase_status=status,
            phase_model=job["model"], phase_effort=job["effort"],
            phase_transition=job["transition"], **accepted)

    def consume(self, message, config):
        rid, method = message.get("id"), message.get("method")
        if method is None and rid in self.starts:
            self.starts.discard(rid)
            tid = ((message.get("result") or {}).get("thread") or {}).get("id")
            if tid and "error" not in message:
                # Durable ownership lets resumed tools return safely even when
                # the experiment is later disabled or the bridge restarts.
                self.owned.add(tid)
                try:
                    atomic_json(self.marker(tid), {"thread": tid, "schema": 1})
                except OSError:
                    self.router.log({"event": "phase_ownership_unavailable"})
        if method is None and isinstance(rid, str) and rid.startswith(self.prefix):
            job = self.pending.pop(rid, None)
            if job:
                status = "applied" if (message.get("result") or {}).get("status") == "applied" else "rejected"
                if status == "applied":
                    row = self.router.threads.get(job["thread"], {})
                    row.update(phase_name=job["phase"], phase_status="accepted",
                        phase_id=job["phase_id"], phase_accepted_at=time.time(),
                        phase_model=job["model"], phase_effort=job["effort"],
                        phase_transition=job["transition"], tier=job["tier"],
                        accepted_model=job["model"], accepted_effort=job["effort"],
                        model=job["model"], effort=job["effort"],
                        confirmation="Aceptado por Codex")
                    # Previous-phase inference evidence must not label the new
                    # accepted settings as already observed.
                    for key in ("observed_model", "observed_effort", "inference_source", "evidence_confidence",
                                "observed_candidate_model", "observed_candidate_effort"):
                        row.pop(key, None)
                else:
                    self.disable_turn(job["thread"])
                self.record(job, status)
                self.reply(job["call"], status)
            return True  # Also consume late responses after timeout/cancellation.
        p = message.get("params") or {}
        if (method != "item/tool/call" or p.get("tool") != TOOL
                or p.get("namespace") is not None or "id" not in message):
            return False
        if not self.owns(p.get("threadId")):
            row = self.router.threads.get(p.get("threadId"), {})
            parent = row.get("parent") or row.get("forked_from")
            if self.owns(parent):
                # Native forks can inherit tools; they are not enrolled roots.
                self.reply(rid, "preserved")
                return True
            return False
        tid, turn = p["threadId"], self.turns.get(p["threadId"])
        args = p.get("arguments")
        if (not isinstance(args, dict) or set(args) != {"phase", "complexity"}
                or args.get("phase") not in PHASES or args.get("complexity") not in TIERS):
            self.reply(rid, "invalid_checkpoint")
            return True
        if (not self.enabled or not config.get("phase_routing") or not config.get("enabled")
                or not turn or turn["id"] != p.get("turnId") or not turn["allowed"]
                or read_mode(self.router.state_dir, tid) == "manual"):
            self.reply(rid, "preserved")
            return True
        if (turn["count"] >= 4 or args["phase"] in turn["seen"]
                or any(j["thread"] == tid for j in self.pending.values())):
            self.reply(rid, "checkpoint_limit")
            return True
        turn["seen"].add(args["phase"])
        turn["count"] += 1
        # A summary follows completed substantive work. It may use the ordinary
        # summary route; other phases retain the turn's established minimum.
        tier = TIERS.index(args["complexity"])
        if args["phase"] != "summarize" and turn["floor"] in TIERS:
            tier = max(tier, TIERS.index(turn["floor"]))
        route = config.get("routes", DEFAULT_ROUTES).get(TIERS[tier], {})
        model, effort = route.get("model"), route.get("effort")
        minimum = turn["min_effort"] if args["phase"] != "summarize" else None
        if minimum in EFFORTS and effort in EFFORTS and EFFORTS.index(effort) < EFFORTS.index(minimum):
            effort = minimum
        row = self.router.threads.get(tid, {})
        source = row.get("accepted_model") or row.get("model")
        job = {"call": rid, "phase_id": uuid.uuid4().hex, "source_model": source, "thread": tid, "turn_id": turn["id"], "decision_id": turn.get("decision_id") or self.router.current_decisions.get(tid), "phase": args["phase"], "model": model,
            "effort": effort, "tier": TIERS[tier], "transition": transition_kind(source, model), "deadline": self.clock() + 10}
        if model == ASTRA and source != ASTRA:
            row["pending_phase_floor"] = "critical"
            row["pending_phase_name"] = args["phase"]
            row["pending_phase_id"] = uuid.uuid4().hex
            self.router.save_task(tid, row)
            self.disable_turn(tid)
            self.record(job, "requires_new_turn")
            self.reply(rid, "requires_new_turn")
        elif (row.get("provider") != "openai" or not source or not model
                or effort not in ("low", "medium", "high", "xhigh")
                or not can_switch_within_turn(source, model) or effort not in self.router.catalog.get(model, set())):
            self.record(job, "preserved")
            self.reply(rid, "preserved")
        elif source == model and (row.get("accepted_effort") or row.get("effort")) == effort:
            self.record(job, "unchanged")
            self.reply(rid, "unchanged")
        else:
            self.sequence += 1
            request = self.prefix + str(self.sequence)
            self.pending[request] = job
            self.record(job, "requested")
            self.router.outbound.append({"id": request, "method": "turn/settings/update",
                "params": {"threadId": tid, "turnId": turn["id"], "model": model, "effort": effort}})
        return True

    def poll(self):
        for rid, job in list(self.pending.items()):
            if self.clock() >= job["deadline"]:
                self.pending.pop(rid)
                self.disable_turn(job["thread"])
                row = self.router.threads.get(job["thread"], {})
                row.update(phase_status="unknown_after_timeout", confirmation="Cambio de fase sin confirmar")
                self.record(job, "unknown_after_timeout")
                self.reply(job["call"], "unknown_after_timeout")
