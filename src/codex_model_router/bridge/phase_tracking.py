"""Conservative, dynamic task plans and observed lifecycle evidence.

The router never claims that Codex completed an internal semantic step. Plans
are derived from requested actions, stored as symbols; only the native turn lifecycle
is marked as observed.
"""

ASTRA = "gpt-6-astra"
from codex_model_router.routing.workload import STEPS, plan_steps
from codex_model_router.routing.model_catalog import MODELS
COMPATIBLE_LIVE_MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"))


def task_plan(category="general", steps=None):
    """Return a content-free plan. Every step remains explicitly planned."""
    labels = {key: label for key, label, _ in STEPS}
    selected = list(dict.fromkeys(key for key in (steps or []) if key in labels))
    return [{"id": key, "label": labels[key], "state": "planned", "evidence": "plan"} for key in selected] or [
        {"id": "solve", "label": "Resolver la petición", "state": "planned", "evidence": "plan"}]


def dynamic_pipeline(category="general", execution_status="proposed", steps=None):
    """Combine a variable plan with one independently observed Codex state."""
    plan = task_plan(category, steps)
    plan.append({"id": "codex_execution", "label": "Ejecución en Codex",
                 "state": execution_status, "evidence": "observed"})
    return plan


def transition_kind(source, destination):
    """Return a safe classification for a potential same-turn model change."""
    if not source or source == destination:
        return "same_model"
    if source == ASTRA or destination == ASTRA:
        return "blocked_astra_boundary"
    if source in COMPATIBLE_LIVE_MODELS and destination in COMPATIBLE_LIVE_MODELS:
        return "compatible_group"
    if {source, destination} == {"gpt-6-luna", "gpt-6.1-sol"}:
        return "blocked_review_boundary"
    return "unverified_transition" if source in MODELS and destination in MODELS else "unknown_model"


def can_switch_within_turn(source, destination):
    """Whether Codex's tested live-switch safety boundary permits the pair."""
    return transition_kind(source, destination) in ("same_model", "compatible_group")


def proposed_phase(source, model, effort, category="general", steps=None):
    """Create a dynamic plan and the proposed observed execution state."""
    return {
        "phase_name": "execution",
        "phase_status": "proposed",
        "phase_model": model,
        "phase_effort": effort,
        "phase_transition": transition_kind(source, model),
        "pipeline_mode": "plan_and_observation",
        "phase_pipeline": dynamic_pipeline(category, steps=steps),
    }


def phase_update(row, status, model=None, effort=None, transition=None):
    """Return a safe update for an observed phase lifecycle event."""
    result = {"phase_name": row.get("phase_name", "execution"), "phase_status": status}
    if model:
        result["phase_model"] = model
    if effort:
        result["phase_effort"] = effort
    if transition:
        result["phase_transition"] = transition
    result["pipeline_mode"] = "plan_and_observation"
    steps = [step.get("id") for step in row.get("phase_pipeline", []) if step.get("evidence") == "plan"]
    result["phase_pipeline"] = dynamic_pipeline(row.get("agent_category", "general"), status, steps)
    return result


def native_plan(params):
    """Project native plan states to content-free labels; discard all free text."""
    plan = params.get("plan")
    turn = params.get("turnId")
    if not isinstance(turn, str) or not turn or not isinstance(plan, list) or len(plan) > 100:
        return None
    labels = {key: label for key, label, _ in STEPS}
    states = {"pending": "pending", "inProgress": "active", "completed": "completed"}
    steps = []
    for index, step in enumerate(plan):
        if not isinstance(step, dict) or step.get("status") not in states or not isinstance(step.get("step"), str):
            return None
        hints = plan_steps(step["step"][:4000])
        label = labels[hints[0]] if hints else "Paso " + str(index + 1)
        steps.append({"id": "step_" + str(index + 1), "label": label,
                      "state": states[step["status"]], "evidence": "native_plan"})
    return {"turn_id": turn, "steps": steps}
