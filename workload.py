"""Content-free task contracts shared by routing and observed plans.

These are conservative signals, not a semantic completion attestation. Only an
explicit completion clears the contract; a neutral progress message does not.
"""
import re
import unicodedata

TIERS = ("simple", "normal", "complex", "critical")
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
STEPS = (
    ("investigate", "Investigar", r"investig\w*|research|diagnostic\w*|analiz\w*|inspect\w*|entender"),
    ("design", "Diseñar", r"disen\w*|design\w*|planificar\w*|arquitectura|architecture"),
    ("implement", "Implementar", r"implement\w*|desarroll\w*|codific\w*|correg\w*|arregl\w*|refactor\w*|build|fix"),
    ("verify", "Validar", r"prueb\w*|test\w*|valid\w*|verific\w*|comprob\w*|check\w*"),
    ("document", "Documentar", r"document\w*|redact\w*|informar|report"),
    ("deliver", "Publicar", r"despleg\w*|desplieg\w*|deploy\w*|public\w*|commit\w*|push|merge\w*"),
)


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def intent_text(text):
    value = normalized(text or "")
    value = re.sub(r"```[\s\S]*?```", " ", value)
    value = re.sub(r"(?m)^\s*>.*$", " ", value)
    return value


def starts_new_task(text):
    return bool(re.match(r"^\s*(?:(?:ok|vale|bien)[,.: ]+)?(?:tengo (?:una )?)?(?:nueva tarea|otra tarea|cambio de tema|new task|new topic)\b", intent_text(text)))


def plan_steps(text):
    """Persist symbolic actions in requested order, never the original prose."""
    value = intent_text(text)
    positions = []
    for key, label, pattern in STEPS:
        for match in re.finditer(r"\b(?:" + pattern + r")\b", value):
            prefix = value[max(0, match.start() - 35):match.start()]
            if re.search(r"\b(?:no|sin|not|without)\s+(?:hay que\s+|hace falta\s+)?$", prefix):
                continue
            positions.append((match.start(), key))
            break
    return [key for _, key in sorted(positions)][:6]


def response_summary(text):
    value = intent_text(text)
    if not value.strip():
        return None
    # Remove explicit negated/completed clauses before extracting pending work.
    closed = bool(re.search(r"\b(?:no (?:queda|hay) (?:nada |trabajo )?pendiente|no queda nada por hacer|todo (?:esta )?(?:terminado|completado|resuelto)|all (?:work|tasks?) (?:is |are )?(?:done|complete)|nothing (?:left|pending)|no remaining work)\b", value))
    clean = re.sub(r"\b(?:no (?:queda|hay) (?:nada |trabajo )?pendiente|sin (?:riesgo|trabajo pendiente)(?: ni (?:riesgo|trabajo pendiente))?|no queda nada por hacer|no remaining work|nothing (?:left|pending))\b", " ", value)
    awaiting = bool(re.search(r"\b(?:cuando me confirmes|cuando digas adelante|si te parece bien|confirma|awaiting|once you confirm|ready to implement)\b", clean))
    planning = bool(re.search(r"\b(?:plan|planificacion|pasos|propuesta|abordaria|lo haria en|primero|despues|then|steps?)\b", clean))
    pending = bool(re.search(r"\b(?:falta(?:n|ba)?|queda(?:n|ba)?|pendiente(?:s)?|por hacer|aun hay|todavia hay|lo siguiente|siguientes? pasos?|remaining|left to do|still needs?|next steps?|outstanding)\b", clean))
    planned_implementation = bool(re.search(r"\b(?:implementar|desarrollar|codificar|aplicar el cambio|implement|build)\b", clean))
    steps = plan_steps(clean)
    unfinished = pending or awaiting or (planning and planned_implementation)
    tests = "verify" in steps
    risk = bool(re.search(r"\b(?:seguridad|security|autentic\w*|autoriz\w*|authentic\w*|authoriz\w*|perdida de datos|data loss|vulnerabil\w*|riesgo)\b", clean))
    complex_work = bool(re.search(r"\b(?:arquitectura|architecture|integr\w*|migraci\w*|migration|refactor\w*|investiga\w*|research|diagnostica\w*|debug\w*|concurrencia|services|servicios|multi.repo)\b", clean))
    floor = "critical" if risk else "complex" if complex_work or (pending and tests) else "normal"
    return {"has_plan": planning, "implementation_pending": unfinished,
            "awaiting_approval": awaiting, "mentions_tests": tests,
            "mentions_deployment": "deliver" in steps, "risk_signals": risk,
            "pending_work": pending, "work_floor": floor,
            "completed": closed and not unfinished,
            "response_kind": "completed" if closed and not unfinished else "plan" if planning and unfinished else "pending_work" if unfinished else "status",
            "plan_steps": steps if unfinished else []}


def merge_contract(previous, summary):
    result = dict(previous or {})
    if not summary:
        return result
    if summary.get("completed"):
        return {"status": "completed", "plan_steps": [], "awaiting_approval": False}
    if summary.get("implementation_pending"):
        floor = summary.get("work_floor", "normal")
        old = result.get("floor")
        if old in TIERS:
            floor = max(old, floor, key=TIERS.index)
        result.update(status="pending", floor=floor,
                      min_effort="high" if floor in ("complex", "critical") else "medium",
                      awaiting_approval=summary.get("awaiting_approval", False))
        if summary.get("plan_steps"):
            result["plan_steps"] = summary["plan_steps"]
    return result


def effective_context(row):
    summary = dict(row.get("response_context") or {})
    contract = row.get("task_contract") or {}
    floor = contract.get("floor") or row.get("task_floor")
    if contract.get("status") == "completed":
        return {"completed": True}
    if floor in TIERS:
        latest = summary.get("work_floor")
        summary.update(implementation_pending=True, pending_work=True,
                       work_floor=max(floor, latest, key=TIERS.index) if latest in TIERS else floor,
                       awaiting_approval=contract.get("awaiting_approval", False))
    return summary or None
