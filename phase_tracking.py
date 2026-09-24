"""Small, conservative phase-state helpers for the router.

This module describes observed lifecycle state. It does not infer semantic
phases from prompts and it never changes a model or an approval policy.
"""

ASTRA = "gpt-6-astra"
COMPATIBLE_LIVE_MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"))


def broad_pipeline(execution_status="proposed"):
    """Return the deliberately broad, content-free observation pipeline.

    Codex does not currently publish trustworthy internal boundaries for a
    task's preparation, review, or delivery work.  Those stages are therefore
    shown as a plan, while only the native turn's execution state is observed.
    """
    return [
        {"id": "preparation", "label": "Preparación", "state": "configured"},
        {"id": "execution", "label": "Ejecución", "state": execution_status},
        {"id": "review", "label": "Revisión", "state": "not_observed"},
        {"id": "closure", "label": "Cierre", "state": "not_observed"},
    ]


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


def proposed_phase(source, model, effort):
    """Create content-free metadata for a proposed execution phase."""
    return {
        "phase_name": "execution",
        "phase_status": "proposed",
        "phase_model": model,
        "phase_effort": effort,
        "phase_transition": transition_kind(source, model),
        "pipeline_mode": "observation",
        "phase_pipeline": broad_pipeline(),
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
    result["pipeline_mode"] = "observation"
    result["phase_pipeline"] = broad_pipeline(status)
    return result
