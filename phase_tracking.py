"""Small, conservative phase-state helpers for the router.

This module describes observed lifecycle state. It does not infer semantic
phases from prompts and it never changes a model or an approval policy.
"""

ASTRA = "gpt-6-astra"
COMPATIBLE_LIVE_MODELS = frozenset(("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"))


def transition_kind(source, destination):
    """Return a safe classification for a potential same-turn model change."""
    if not source or source == destination:
        return "same_model"
    if source == ASTRA or destination == ASTRA:
        return "blocked_astra_boundary"
    if source in COMPATIBLE_LIVE_MODELS and destination in COMPATIBLE_LIVE_MODELS:
        return "compatible_group"
    return "unknown_model"


def proposed_phase(source, model, effort):
    """Create content-free metadata for a proposed execution phase."""
    return {
        "phase_name": "execution",
        "phase_status": "proposed",
        "phase_model": model,
        "phase_effort": effort,
        "phase_transition": transition_kind(source, model),
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
    return result
