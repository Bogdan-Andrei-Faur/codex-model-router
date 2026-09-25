"""Quality-first ES/EN policy: model and reasoning are separate choices.
Workload mappings are personal policy, not measured superiority claims.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import re
import unicodedata
from workload import response_summary, starts_new_task, intent_text

TIERS = ("simple", "normal", "complex", "critical")
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
EFFORT_LABELS = dict(zip(EFFORTS, ("Ligero", "Medio", "Alto", "Muy alto", "Máx.", "Ultra")))
AGENT_CATEGORIES = ("interface", "correction", "tests", "audit", "architecture", "text", "research", "configuration", "automation", "general")
DEFAULT_ROUTES = {
    "simple": {"model": "gpt-5.6-luna", "effort": "low"},
    "normal": {"model": "gpt-5.6-terra", "effort": "medium"},
    "complex": {"model": "gpt-5.6-sol", "effort": "high"},
    "critical": {"model": "gpt-6-astra", "effort": "xhigh"},
}

@dataclass(frozen=True)
class Decision:
    tier: str
    reason: str
    effort: str = "medium"
    quality_floor: str | None = None
    request_kind: str = "task"
    max_effort_allowed: bool = False

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))

def has(pattern, text):
    return bool(re.search(pattern, text))


def classify_agent_identity(text, title="", attachments=False, model_reason="", previous=None):
    """Return privacy-safe agent identity metadata without retaining user content.

    A title is a stronger signal than the current message. The message is only
    inspected at routing time; the returned category/confidence contain no text.
    """
    title = normalize(title)
    message = normalize(text)
    reason = normalize(model_reason)
    patterns = (
        ("audit", r"\b(auditor\w*|audit\w*|seguridad|security|vulnerabil\w*|accesibilidad|accessibility|compliance)\b"),
        ("interface", r"\b(ui\s*/?\s*ux|ux|ui|interfaz|interfaces|frontend|front.end|figma|disen\w*|redisen\w*|maquet\w*|layout|responsive|tipografia|animacion\w*|visual)\b"),
        ("tests", r"\b(prueba\w*|test\w*|e2e|validar|verificar|comprobar|coverage)\b"),
        ("correction", r"\b(correg\w*|arregl\w*|error|fallo|bug|fix\w*|regresion|regression)\b"),
        ("architecture", r"\b(arquitectura|architecture|migraci\w*|migration|refactor\w*|concurrencia|deadlock|distribuid\w*)\b"),
        ("research", r"\b(investig\w*|research|diagnostic\w*|causa raiz|root cause|analiz\w*|rendimiento|performance|compar\w*|optimiza\w*)\b"),
        ("configuration", r"\b(configur\w*|instal\w*|deploy\w*|desplieg\w*|dependenc\w*|entorno|environment|docker|npm|pip|ci/cd)\b"),
        ("automation", r"\b(automat\w*|programa\w*|script\w*|workflow|cron|orquest\w*)\b"),
        ("text", r"\b(traduc\w*|translat\w*|texto\w*|document\w*|resum\w*|redact\w*|ortografia|typo|reformula\w*)\b"),
    )
    scores = {}
    for category, pattern in patterns:
        # A specific title should win over a generic follow-up such as “sí”.
        scores[category] = 3 * len(re.findall(pattern, title)) + 2 * len(re.findall(pattern, message)) + len(re.findall(pattern, reason))
    category, score = max(scores.items(), key=lambda item: item[1])
    if score:
        return category, "alta" if score >= 3 else "media"
    if attachments:
        return "interface", "baja"
    if previous in AGENT_CATEGORIES and previous != "general":
        return previous, "heredada"
    return "general", "baja"

def lightweight_request(intent):
    """Recognize whole, bounded messages, never just a short prefix or length."""
    sentence = re.sub(r"[¿?¡!.,;:]+", " ", intent)
    sentence = re.sub(r"\s+", " ", sentence).strip()
    acknowledgement = (
        r"(?:(?:ok|vale|perfecto|genial|gracias|thanks|thank you|great)[ ]*)+|"
        r"(?:parece que |looks like |it looks like )?(?:ahora |ya |now )?(?:si |it )?"
        r"(?:esta funcionando|funciona|funciona bien|funciona correctamente|works|is working|works now|is working now)"
    )
    if re.fullmatch(acknowledgement, sentence):
        return "acknowledgement"
    status_check = (
        r"(?:(?:ok|vale|ahora|por favor) )*"
        r"(?:comprueba|consulta|mira|dime|verifica) "
        r"(?:(?:cuantas|cuantos) (?:solicitudes|eventos|inferencias|registros) "
        r"(?:de telemetria )?han llegado|(?:el estado|los contadores) (?:de la telemetria|del receptor))|"
        r"(?:please )?(?:check|show|tell me) (?:the )?(?:telemetry counters|receiver status|"
        r"how many (?:telemetry )?(?:requests|events|inferences) (?:have arrived|were received))"
    )
    if re.fullmatch(status_check, sentence):
        return "status_check"
    return None


def summarize_response_context(text):
    return response_summary(text)


def resumes_previous_work(intent):
    """Recognize instructions to resume work, not courtesy before a new request."""
    intent = re.sub(r"^(?:(?:si|yes|ok|vale|perfecto|please|por favor)\b[\s,.:;!]*)+", "", intent)
    return has(
        r"^(?:continua|continue|sigue|proceed|adelante|hazlo|do it|implementalo|"
        r"arreglalo|ejecutalo|compruebalo)\b|"
        r"^(?:ahora\s+)?(?:implementa|implement|haz|ejecuta|termina|completa|finish|do)\s+"
        r"(?:lo\s+(?:que\s+)?(?:acordamos|acordado|pendiente|falta)|el\s+plan|"
        r"los\s+(?:pasos|puntos)\s+pendientes|the\s+(?:plan|remaining\s+work))\b|"
        r"^ahora\s+(?:hazlo|implementalo|arreglalo|ejecutalo|compruebalo)\b|"
        r"^haz\s+lo\s+que\s+(?:consideres|creas)\s+necesario(?:\s+para\s+dejarlo\s+bien)?[.!\s]*$", intent)


def classify(text, previous=None, attachments=False, previous_effort=None, response_context=None):
    t = normalize(text).strip()
    intent = intent_text(text)
    new_task = starts_new_task(text)
    if new_task:
        response_context = None
        previous = None
    if response_context and response_context.get("completed"):
        previous = None
    previous = previous if previous in TIERS else None
    prior_effort = previous_effort if previous_effort in EFFORTS else DEFAULT_ROUTES.get(previous, {}).get("effort", "medium")
    failure = has(r"\b(sigue fallando|no funciona|mismo error|still fails|still broken|did not work|no lo has solucionado)\b", intent)
    hard = has(r"\b(exhaustiv\w*|exhaustive|profund[ao]|deep|complet[ao]|integral|end.to.end|de principio a fin|varios repos\w*|multi.repo)\b", intent)
    risk = has(r"\b(perdida de datos|data loss|corrupcion de datos|data corruption|production outage|ransomware|doble asignacion|double assignment|interlock|seguridad industrial|parada de emergencia|autenticacion|authentication|autorizacion|authorization|vulnerabil\w*|security audit)\b", intent)
    audit = has(r"\b(audita\w*|audit\w*|revision integral|revision de seguridad|security review)\b", intent)
    visual = has(r"\b(ui\s*/?\s*ux|ux|ui|interfaces?|interface|frontend|front.end|figma|diseno visual|visual design|redisen\w*|redesign|landing|maquet\w*|layout|accesibilidad|accessibility|responsive|tipografia|typography|animacion\w*|animation\w*)\b", intent)
    mechanical = has(r"\b(solo|solamente|unicamente|just|only)\b", intent) and has(r"\b(color|texto|label|etiqueta|margen|margin|padding|rename|renombra\w*|ortografia|typo|icono|icon)\b", intent)
    design = has(r"\b(disen\w*|design|redisen\w*|redesign|crea\w*|build|implement\w*|mejora\w*|improve|evalua\w*|analiza\w*|analy\w*|revisa\w*|review)\b", intent)
    architecture = has(r"\b(arquitectura|architecture|migracion|migration|concurrencia|concurrency|condicion de carrera|race condition|deadlock|distribuid\w*|distributed|refactor\w*)\b", intent)
    investigation = has(r"\b(investiga\w*|investigate|diagnostica\w*|diagnos\w*|causa raiz|root cause|optimiza\w*|optimize|rendimiento|performance|compara\w*|trade.off)\b", intent)
    edit = has(r"\b(implement\w*|crea\w*|anade\w*|agrega\w*|construye|build|create|add|arregla\w*|corrige\w*|fix|cambia\w*|change|modifica\w*|modify|borra\w*|delete|ejecuta\w*|execute|run|configura\w*|configure|despliega\w*|deploy|instala\w*|install)\b", intent)
    simple = has(r"\b(traduce|traducir|translate|translation|resume|resumen|summarize|summary|ortografia|spelling|explica|explain|que significa|what does|que es|what is|cuanto es|how much|saluda|hola|hello|reformula|rephrase|formatea|format|titulo|title)\b", intent)
    testing = has(r"\b(prueb\w*|test\w*|valid\w*|verific\w*|comprobar\w*|check\w*|smoke|e2e|regresi\w*)\b", intent)
    broad_testing = testing and has(r"\b(tod\w*|todas|todo lo que haga falta|que haga falta|necesari\w*|exhaustiv\w*|complet\w*|integral\w*)\b", intent)
    lightweight = lightweight_request(intent) if not attachments else None
    prior_plan = response_context and response_context.get("implementation_pending")
    context_floor = response_context.get("work_floor") if isinstance(response_context, dict) else None
    execute_previous = resumes_previous_work(intent) and not new_task
    bounded_transform = has(r"^(?:(?:nueva tarea|new task)\s*:\s*)?(?:traduce|traducir|translate|reformula|rephrase|formatea|format)\b", intent)
    if bounded_transform and not attachments:
        result = Decision("simple", "transformación delimitada del texto aportado", "low", request_kind="bounded")
    elif risk or audit:
        result = Decision("critical", "auditoría, revisión rigurosa o consecuencias importantes", "max" if hard and risk else "xhigh",
                          quality_floor="critical", max_effort_allowed=bool(hard and risk))
    elif visual and (design or attachments) and not mechanical:
        result = Decision("critical", "diseño de interfaces, UX o evaluación visual", "xhigh" if hard or has(r"redisen|redesign|ux|figma", intent) else "high", quality_floor="critical")
    elif attachments and not mechanical:
        result = Decision("critical", "interpretación de adjuntos y referencias visuales", "high", quality_floor="critical")
    elif (architecture and hard) or (investigation and hard) or len(t) > 10000:
        result = Decision("critical", "trabajo amplio que requiere la máxima capacidad", "xhigh", quality_floor="critical")
    elif architecture or investigation or len(t) > 4000:
        result = Decision("complex", "ingeniería compleja con alcance definido", "xhigh" if failure else "high", quality_floor="complex")
    elif testing:
        result = Decision("complex" if broad_testing else "normal",
                          "validación técnica y pruebas de la tarea" if not broad_testing else "validación amplia con todas las pruebas necesarias",
                          "high" if broad_testing else "medium",
                          quality_floor="complex" if broad_testing else "normal")
    elif lightweight:
        if prior_plan and response_context.get("awaiting_approval") and lightweight == "acknowledgement" and not has(r"\b(gracias|thanks|thank you)\b", intent):
            result = Decision(context_floor or "normal", "confirmación de trabajo pendiente en la respuesta anterior", "medium",
                              quality_floor=context_floor or "normal", request_kind="planned_followup")
        else:
            result = Decision("simple" if lightweight == "acknowledgement" else "normal",
                          "confirmación de resultado" if lightweight == "acknowledgement" else "consulta acotada de estado o contadores",
                          "low" if lightweight == "acknowledgement" else "medium", request_kind=lightweight)
    elif edit:
        result = Decision("normal", "cambio concreto y comprobable", "low" if mechanical else "medium")
    elif simple and len(t) < 1800:
        result = Decision("simple", "consulta o transformación delimitada", "medium" if has(r"explica|explain|resume|summary", intent) else "low", request_kind="bounded")
    else:
        result = Decision("complex", "petición ambigua: conservar capacidad", "medium", request_kind="ambiguous")
    # Persisted unfinished work constrains requests that actually resume it.
    # Independent requests are evaluated on their own current risk signals.
    if (execute_previous and prior_plan and context_floor in TIERS and
            result.request_kind not in ("acknowledgement", "status_check", "bounded") and
            (result.quality_floor is None or TIERS.index(result.quality_floor) < TIERS.index(context_floor))):
        minimum_effort = DEFAULT_ROUTES.get(context_floor, {}).get("effort", result.effort)
        result = Decision(context_floor, "trabajo técnico pendiente en la respuesta anterior",
                          max(result.effort, minimum_effort, key=EFFORTS.index),
                          quality_floor=context_floor, request_kind="planned_followup")
    if failure and previous:
        index = min(TIERS.index(previous) + 1, 3)
        if index >= TIERS.index(result.tier):
            effort = "max" if previous == "critical" and prior_effort in ("xhigh", "max") else "xhigh" if index == 3 else "high"
            result = Decision(TIERS[index], "el intento anterior no resolvió la tarea", effort,
                              quality_floor=TIERS[index], request_kind="retry", max_effort_allowed=effort == "max")
    continuation = has(r"^(si\b|yes\b|continua\b|sigue\b|adelante\b|continue\b|proceed\b|hazlo\b|do it\b|ok\b|vale\b|y ahora\b|and now\b|eso\b|lo mismo\b|that\b|ahora\b|[¿?]*por que\b|[¿?]*why\b|[¿?]*que (modelo|numero)\b)", intent)
    if previous and (execute_previous or (continuation and result.request_kind == "ambiguous")) and not new_task and not failure and result.request_kind not in ("acknowledgement", "status_check", "bounded"):
        if result.quality_floor is None or TIERS.index(result.quality_floor) <= TIERS.index(previous):
            # A request to carry out the agreed work needs its existing capacity.
            # A generic follow-up is only a fallback preference, not a hard floor.
            floors = [tier for tier in (previous if execute_previous else None, result.quality_floor, context_floor if execute_previous else None) if tier in TIERS]
            floor = max(floors, key=TIERS.index) if floors else None
            minimum_effort = DEFAULT_ROUTES.get(floor, {}).get("effort", result.effort)
            effort = max(prior_effort, result.effort, minimum_effort, key=EFFORTS.index) if floor else prior_effort
            if not result.max_effort_allowed:
                effort = min(effort, "xhigh", key=EFFORTS.index)
            followup_kind = "planned_followup" if prior_plan and execute_previous else "work_followup" if execute_previous else "context_followup"
            result = Decision(floor or previous, "continuación: conservar capacidad y reevaluar razonamiento", effort,
                              quality_floor=floor, request_kind=followup_kind,
                              max_effort_allowed=result.max_effort_allowed)
    if result.quality_floor in ("complex", "critical") and EFFORTS.index(result.effort) < EFFORTS.index("high"):
        result = replace(result, effort="high")
    return result

def explicit_model(text, routes):
    names = {"luna": "simple", "terra": "normal", "sol": "complex", "astra": "critical"}
    m = re.match(r"^\s*(?:usa|utiliza|use|con el modelo|modelo)\s+(?:el modelo\s+)?(?:gpt-[\d.]+-)?(luna|terra|sol|astra)\b", normalize(text))
    return dict(routes[names[m.group(1)]]) if m else None

def select_route(text, routes, previous=None, previous_effort=None, attachments=False):
    route, reasons = select_route_details(text, routes, previous, previous_effort, attachments)
    return route, reasons["model"]

def select_route_details(text, routes, previous=None, previous_effort=None, attachments=False, response_context=None):
    decision = classify(text, previous, attachments, previous_effort, response_context)
    explicit = explicit_model(text, routes)
    route = explicit or {"model": routes[decision.tier]["model"], "effort": decision.effort}
    t = normalize(text).split("```", 1)[0]
    # Only commands at the start qualify, never discussion/quotes about Ultra.
    directive = re.match(r"^\s*(?:(?:usa|utiliza|use)\s+(?:(?:el modelo\s+)?(?:gpt-[\d.]+-)?(?:luna|terra|sol|astra)\s*[,.:]?\s*(?:con\s+)?|(?:un\s+)?))?(?:con\s+)?(?:esfuerzo|razonamiento|reasoning|effort)\s+(?:de\s+)?", t)
    m = re.match(r"(muy alto|extra high|xhigh|maximo|max|ultra|ligero|low|medio|medium|alto|high)\b", t[directive.end():]) if directive else None
    if m:
        labels = {"ligero": "low", "medio": "medium", "alto": "high", "muy alto": "xhigh", "extra high": "xhigh", "maximo": "max"}
        route["effort"] = labels.get(m.group(1), m.group(1))
    # Ultra also enables proactive delegation: only select it explicitly.
    if route["effort"] == "ultra" and not m and previous_effort != "ultra":
        route["effort"] = "max"
    if explicit:
        model_reason = "modelo indicado explícitamente"
    else:
        model_reason = decision.reason
    if m:
        effort_reason = "nivel de razonamiento indicado explícitamente"
    elif decision.reason.startswith("continuación"):
        effort_reason = "continuación de trabajo; Máx. requiere nuevas señales de riesgo o de fallo"
    elif decision.reason.startswith("el intento anterior"):
        effort_reason = "mayor profundidad tras un intento que no resolvió la tarea"
    else:
        effort_reason = {
            "low": "tarea delimitada: razonamiento ligero",
            "medium": "análisis moderado para una tarea concreta",
            "high": "trabajo complejo o revisión visual que requiere más profundidad",
            "xhigh": "revisión profunda por amplitud, UX, auditoría o consecuencias",
            "max": "máxima profundidad por riesgo o alcance excepcional",
            "ultra": "delegación y profundidad Ultra solicitadas explícitamente",
        }.get(route["effort"], "nivel configurado para esta categoría")
    source = "explicit" if explicit or m else "automatic"
    retry = has(r"\b(sigue fallando|no funciona|mismo error|still fails|still broken|did not work|no lo has solucionado)\b", normalize(text))
    return route, {"model": model_reason, "effort": effort_reason, "source": source,
                   "signal": "retry" if retry else None, "quality_floor": decision.quality_floor,
                   "min_effort": ("high" if decision.quality_floor in ("complex", "critical") else "medium" if decision.quality_floor == "normal" and decision.effort != "low" else "low"),
                   "request_kind": decision.request_kind, "max_effort_allowed": decision.max_effort_allowed,
                   "new_task": starts_new_task(text)}

def user_text(items):
    return "\n".join(x.get("text", "") for x in items if isinstance(x, dict) and x.get("type") == "text")

def has_attachments(items):
    return any(isinstance(x, dict) and x.get("type") != "text" for x in items)
