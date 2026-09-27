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


def cancels_work(text):
    return bool(re.match(r"^\s*(?:(?:ok|vale|ahora|por favor|please)[, ]+)*(?:cancela\b|cancel\b|deten\b|stop\b|no (?:continues|sigas)\b|abandona\b)", intent_text(text)))


def resumes_work(text):
    value = intent_text(text)
    if cancels_work(value) or re.search(r"\b(?:no|not|don't)\b", value):
        return False
    # An explicit model prefix may precede the continuation instruction.
    value = re.sub(r"^\s*(?:usa|utiliza|use)\s+(?:el modelo\s+)?(?:gpt-[\d.]+-)?(?:luna|terra|sol|astra)\b[^:;\n]*[:;]\s*", "", value)
    return bool(re.match(r"^\s*(?:(?:ok|vale|si|yes|ahora|por favor|please)[, ]+)*(?:continua\b|continue\b|proceed\b|adelante\b|dale\b|hazlo\b|do it\b|sigue\b|reanuda\b|resume\b|(?:implementa|ejecuta|comprueba|verifica) (?:lo acordado|lo pendiente|la fase)\b)", value))


def critical_risk(value):
    """Concrete consequences or an explicit audit, not a generic auth mention."""
    return bool(re.search(r"\b(?:perdida de datos|data loss|corrupcion de datos|data corruption|"
                         r"production outage|ransomware|doble asignacion|double assignment|interlock|"
                         r"seguridad industrial|parada de emergencia|vulnerabil\w*)\b", value))


def context_for_engine(context):
    """Allowlisted workload metadata; no transcript, titles or arbitrary values."""
    if not isinstance(context, dict):
        return None
    result = {key: context[key] for key in ("has_plan", "implementation_pending", "awaiting_approval",
              "mentions_tests", "mentions_deployment", "risk_signals", "pending_work", "completed",
              "legacy_uncertain") if type(context.get(key)) is bool}
    if context.get("work_floor") in TIERS:
        result["work_floor"] = context["work_floor"]
    if context.get("response_kind") in ("completed", "plan", "pending_work", "status", "progress"):
        result["response_kind"] = context["response_kind"]
    steps = context.get("plan_steps")
    if isinstance(steps, list):
        result["plan_steps"] = [step for step in dict.fromkeys(x for x in steps if isinstance(x, str))
                                if step in {entry[0] for entry in STEPS}][:6]
    return result or None


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
    remaining = re.search(r"\b(?:solo queda(?:n)?|unicamente falta(?:n)?|only remaining work(?: is)?)\b(.*)", clean, re.S)
    scope_text = remaining.group(1) if remaining else clean
    risk = critical_risk(scope_text)
    complex_work = bool(re.search(r"\b(?:arquitectura|architecture|integr\w*|migraci\w*|migration|refactor\w*|investiga\w*|research|diagnostica\w*|debug\w*|concurrencia|services|servicios|multi.repo|autentic\w*|autoriz\w*|authentic\w*|authoriz\w*)\b", scope_text))
    if remaining:
        steps = plan_steps(scope_text)
        tests = "verify" in steps
    floor = "critical" if risk else "complex" if complex_work or (pending and tests) else "normal"
    return {"has_plan": planning, "implementation_pending": unfinished,
            "awaiting_approval": awaiting, "mentions_tests": tests,
            "mentions_deployment": "deliver" in steps, "risk_signals": risk,
            "pending_work": pending, "work_floor": floor,
            "completed": closed and not unfinished,
            "response_kind": "completed" if closed and not unfinished else "plan" if planning and unfinished else "pending_work" if unfinished else "status",
            "plan_steps": steps if unfinished else [], "contract_version": 2,
            "scope_reassessed": bool(remaining)}


def merge_contract(previous, summary):
    result = dict(previous or {})
    if not summary:
        return result
    if summary.get("completed"):
        return {"status": "completed", "plan_steps": [], "awaiting_approval": False, "version": 2}
    if summary.get("implementation_pending"):
        floor = summary.get("work_floor", "normal")
        old = result.get("floor")
        # Only an explicit final narrowing of remaining work can lower a known
        # floor; generic plans/progress may be talking about just one substep.
        narrow = summary.get("scope_reassessed") and summary.get("response_kind") != "progress"
        if old in TIERS and not narrow:
            if result.get("version") != 2 and old == "critical":
                old = "complex"  # Old contracts did not distinguish auth from risk.
            floor = max(old, floor, key=TIERS.index)
        result.update(status="pending", floor=floor,
                      min_effort="high" if floor in ("complex", "critical") else "medium",
                      awaiting_approval=summary.get("awaiting_approval", False),
                      version=2 if summary.get("contract_version") == 2 else result.get("version", 1))
        if summary.get("plan_steps") or narrow:
            result["plan_steps"] = summary.get("plan_steps", [])
    return result


def effective_context(row):
    summary = dict(row.get("response_context") or {})
    contract = row.get("task_contract") or {}
    floor = contract.get("floor") or row.get("task_floor")
    if contract.get("status") == "completed":
        return {"completed": True}
    if floor in TIERS:
        if floor == "critical" and contract.get("version") != 2:
            floor = "complex"
            summary["legacy_uncertain"] = True
        latest = summary.get("work_floor")
        if latest == "critical" and summary.get("contract_version") != 2:
            latest = "complex"
        summary.update(implementation_pending=True, pending_work=True,
                       work_floor=max(floor, latest, key=TIERS.index) if latest in TIERS else floor,
                       awaiting_approval=contract.get("awaiting_approval", False))
        summary["plan_steps"] = contract.get("plan_steps") or summary.get("plan_steps", [])
    return summary or None
