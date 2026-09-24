"""Conservative, dynamic task plans and observed lifecycle evidence.

The router never claims that Codex completed an internal semantic step. Plans
are derived from the privacy-safe task category; only the native turn lifecycle
is marked as observed.
"""

ASTRA = "gpt-6-astra"
COMPATIBLE_LIVE_MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"))


PLAN_TEMPLATES = {
    "text": (("deliver", "Responder"),),
    "research": (("investigate", "Investigar"), ("decide", "Decidir"), ("deliver", "Entregar")),
    "interface": (("review", "Revisar interfaz"), ("implement", "Implementar"), ("validate", "Comprobar")),
    "correction": (("diagnose", "Diagnosticar"), ("fix", "Corregir"), ("validate", "Validar")),
    "tests": (("inspect", "Revisar"), ("verify", "Verificar"), ("report", "Informar")),
    "audit": (("inspect", "Inspeccionar"), ("assess", "Evaluar"), ("report", "Informar")),
    "architecture": (("map", "Entender"), ("design", "Diseñar"), ("review", "Revisar")),
    "configuration": (("prepare", "Preparar"), ("apply", "Aplicar"), ("verify", "Comprobar")),
    "automation": (("design", "Diseñar"), ("automate", "Automatizar"), ("verify", "Comprobar")),
    "general": (("solve", "Resolver"),),
}


def task_plan(category="general"):
    """Return a content-free plan. Every step remains explicitly planned."""
    return [{"id": step_id, "label": label, "state": "planned", "evidence": "plan"}
            for step_id, label in PLAN_TEMPLATES.get(category, PLAN_TEMPLATES["general"])]


def dynamic_pipeline(category="general", execution_status="proposed"):
    """Combine a variable plan with one independently observed Codex state."""
    plan = task_plan(category)
    plan[0]["state"] = "selected"
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
    return "unknown_model"


def can_switch_within_turn(source, destination):
    """Whether Codex's tested live-switch safety boundary permits the pair."""
    return transition_kind(source, destination) in ("same_model", "compatible_group")


def proposed_phase(source, model, effort, category="general"):
    """Create a dynamic plan and the proposed observed execution state."""
    return {
        "phase_name": "execution",
        "phase_status": "proposed",
        "phase_model": model,
        "phase_effort": effort,
        "phase_transition": transition_kind(source, model),
        "pipeline_mode": "plan_and_observation",
        "phase_pipeline": dynamic_pipeline(category),
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
    result["phase_pipeline"] = dynamic_pipeline(row.get("agent_category", "general"), status)
    return result
