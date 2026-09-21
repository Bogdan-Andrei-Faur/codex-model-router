"""Quality-first ES/EN policy: model and reasoning are separate choices.
Workload mappings are personal policy, not measured superiority claims.
"""
from dataclasses import dataclass
import re
import unicodedata

TIERS = ("simple", "normal", "complex", "critical")
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
EFFORT_LABELS = dict(zip(EFFORTS, ("Ligero", "Medio", "Alto", "Muy alto", "Máx.", "Ultra")))
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

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))

def has(pattern, text):
    return bool(re.search(pattern, text))

def classify(text, previous=None, attachments=False, previous_effort=None):
    t = normalize(text).strip()
    intent = re.sub(r"```[\s\S]*?```", " [code] ", t)
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
    if risk or audit:
        result = Decision("critical", "auditoría, revisión rigurosa o consecuencias importantes", "max" if hard and risk else "xhigh")
    elif visual and (design or attachments) and not mechanical:
        result = Decision("critical", "diseño de interfaces, UX o evaluación visual", "xhigh" if hard or has(r"redisen|redesign|ux|figma", intent) else "high")
    elif attachments and not mechanical:
        result = Decision("critical", "interpretación de adjuntos y referencias visuales", "high")
    elif (architecture and hard) or (investigation and hard) or len(t) > 10000:
        result = Decision("critical", "trabajo amplio que requiere la máxima capacidad", "xhigh")
    elif architecture or investigation or len(t) > 4000:
        result = Decision("complex", "ingeniería compleja con alcance definido", "xhigh" if failure else "high")
    elif edit:
        result = Decision("normal", "cambio concreto y comprobable", "low" if mechanical else "medium")
    elif simple and len(t) < 1800:
        result = Decision("simple", "consulta o transformación delimitada", "medium" if has(r"explica|explain|resume|summary", intent) else "low")
    else:
        result = Decision("complex", "petición ambigua: conservar capacidad", "medium")
    if failure and previous:
        index = min(TIERS.index(previous) + 1, 3)
        if index >= TIERS.index(result.tier):
            effort = "max" if previous == "critical" and prior_effort in ("xhigh", "max") else "xhigh" if index == 3 else "high"
            result = Decision(TIERS[index], "el intento anterior no resolvió la tarea", effort)
    new_task = has(r"\b(nueva tarea|otra tarea|cambio de tema|new task|new topic)\b", intent)
    continuation = has(r"^(si\b|yes\b|continua\b|sigue\b|adelante\b|continue\b|proceed\b|hazlo\b|do it\b|ok\b|vale\b|y ahora\b|and now\b|eso\b|lo mismo\b|that\b|ahora\b|[¿?]*por que\b|[¿?]*why\b|[¿?]*que (modelo|numero)\b)", intent)
    if previous and continuation and not new_task and not failure:
        if not (risk or audit or visual or architecture or investigation or edit) or TIERS.index(result.tier) <= TIERS.index(previous):
            result = Decision(previous, "continuación: conservar modelo y razonamiento", prior_effort)
    return result

def explicit_model(text, routes):
    names = {"luna": "simple", "terra": "normal", "sol": "complex", "astra": "critical"}
    m = re.match(r"^\s*(?:usa|utiliza|use|con el modelo|modelo)\s+(?:el modelo\s+)?(?:gpt-[\d.]+-)?(luna|terra|sol|astra)\b", normalize(text))
    return dict(routes[names[m.group(1)]]) if m else None

def select_route(text, routes, previous=None, previous_effort=None, attachments=False):
    route, reasons = select_route_details(text, routes, previous, previous_effort, attachments)
    return route, reasons["model"]

def select_route_details(text, routes, previous=None, previous_effort=None, attachments=False):
    decision = classify(text, previous, attachments, previous_effort)
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
        effort_reason = "continuación: conservar el nivel de razonamiento anterior"
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
                   "signal": "retry" if retry else None}

def user_text(items):
    return "\n".join(x.get("text", "") for x in items if isinstance(x, dict) and x.get("type") == "text")

def has_attachments(items):
    return any(isinstance(x, dict) and x.get("type") != "text" for x in items)
