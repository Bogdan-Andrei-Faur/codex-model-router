"""Optional decision engines for the personal Codex router.

The engines receive a single, transient routing state. They never write prompt
text, attachment contents, credentials or model output to disk. Every failure
returns control to the deterministic local policy.
"""
import ctypes
from ctypes import wintypes
import json
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


ENGINE_RULES = "rules"
ENGINE_JEV = "jev"
ENGINES = (ENGINE_RULES, ENGINE_JEV)
_KEYCHAIN_TIMEOUT_SECONDS = 45
_KEYCHAIN_CACHE = {}


def attachment_summary(items):
    """Return metadata only; never retain attachment payloads."""
    attachments = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") == "text":
            continue
        kind = str(item.get("type") or "attachment")
        mime = str(item.get("mimeType") or item.get("mime_type") or item.get("content_type") or "")
        attachments.append({"type": kind, "mime": mime})
    return {"present": bool(attachments), "count": len(attachments),
            "images": sum(1 for item in attachments if "image" in item["type"].lower() or item["mime"].lower().startswith("image/")),
            "types": sorted({item["type"] for item in attachments})}


def candidate_routes(routes, catalog):
    """Create the valid model/effort pairs that a classifier may select."""
    preferences = {
        "simple": ("low", "medium"),
        "normal": ("low", "medium", "high"),
        "complex": ("medium", "high", "xhigh"),
        "critical": ("high", "xhigh", "max"),
    }
    names = {"simple": "Luna", "normal": "Terra", "complex": "Sol", "critical": "Astra"}
    descriptions = {
        "simple": "transformación o consulta breve y delimitada",
        "normal": "cambio concreto y comprobable",
        "complex": "ingeniería compleja con alcance definido",
        "critical": "UX, auditoría, adjuntos o trabajo de gran alcance",
    }
    choices = {}
    for tier, route in routes.items():
        model = route.get("model")
        available = catalog.get(model, set())
        for effort in preferences.get(tier, (route.get("effort", "medium"),)):
            if effort in available:
                key = "%s_%s" % (tier, effort)
                choices[key] = {"model": model, "effort": effort, "tier": tier,
                                "label": "%s · %s" % (names.get(tier, tier.title()), effort),
                                "description": descriptions.get(tier, "tarea de Codex")}
    return choices


def build_state(text, attachments, previous_model, previous_effort, failure):
    """Keep the request compact and make attachment presence explicit to text-only engines."""
    return {
        "task": text,
        "attachments": attachments,
        "previous_model": previous_model or None,
        "previous_effort": previous_effort or None,
        "previous_attempt_failed": bool(failure),
        "language": "es",
    }


def _post_json(url, payload, headers=None, timeout=4.0):
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def token_count(value):
    """Normalize provider token counters without retaining request or response content."""
    try:
        value = int(value)
        return value if value >= 0 else None
    except (TypeError, ValueError):
        return None


def engine_usage(response):
    """Extract only aggregate counters from known provider response shapes."""
    usage = response.get("usage") if isinstance(response, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    values = {
        "engine_input_tokens": usage.get("input_tokens", usage.get("inputTokens", usage.get("prompt_tokens", response.get("prompt_eval_count") if isinstance(response, dict) else None))),
        "engine_output_tokens": usage.get("output_tokens", usage.get("outputTokens", usage.get("completion_tokens", response.get("eval_count") if isinstance(response, dict) else None))),
        "engine_cached_tokens": usage.get("cached_input_tokens", usage.get("cached_tokens")),
    }
    return {key: count for key, value in values.items() if (count := token_count(value)) is not None}


def engine_failure(error):
    """Return a stable, content-free failure class for aggregate telemetry."""
    if isinstance(error, urllib.error.HTTPError):
        if error.code == 401:
            return "authentication"
        if error.code == 403:
            return "forbidden"
        if error.code == 429:
            return "rate_limited"
        if error.code in (408, 504):
            return "timeout"
        return "http_%s" % error.code
    if isinstance(error, (socket.timeout, TimeoutError)):
        return "timeout"
    if isinstance(error, urllib.error.URLError):
        reason = getattr(error, "reason", None)
        return "timeout" if isinstance(reason, (socket.timeout, TimeoutError)) else "network"
    return "transport"


def _unprotect_windows(data):
    """Read the DPAPI blob written by the WPF settings panel for this Windows user."""
    if os.name != "nt" or not data:
        return None

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    raw = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), raw)
    target = Blob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        return None
    try:
        return ctypes.string_at(target.pbData, target.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(target.pbData)


def _keychain_key(state_dir, key_id):
    """Read and cache an authorized classifier key; never log its value."""
    if sys.platform != "darwin" or key_id != "jev":
        return None
    state = Path(state_dir).resolve()
    root = str(state.parent)
    service = "local.codex-model-router." + hashlib.sha256(root.encode("utf-8")).hexdigest()
    try:
        revisions = json.loads((state / "keychain-revision.json").read_text(encoding="utf-8"))
        revision = revisions.get(key_id) if isinstance(revisions, dict) else None
    except (OSError, UnicodeError, ValueError):
        revision = None
    cache_key = (service, key_id)
    cached = _KEYCHAIN_CACHE.get(cache_key)
    if cached and cached[0] == revision:
        return cached[1]
    try:
        result = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", service,
                                 "-a", key_id, "-w"], capture_output=True,
                                timeout=_KEYCHAIN_TIMEOUT_SECONDS)
        value = result.stdout.decode("utf-8").strip() if result.returncode == 0 else ""
        if value:
            _KEYCHAIN_CACHE[cache_key] = (revision, value)
            return value
        return None
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        return None


def jev_key(state_dir, connection="typesafe"):
    """Environment variables are useful for development; production key stays DPAPI-protected."""
    value = os.environ.get("PERSONAL_CODEX_JEV_API_KEY")
    if not value:
        value = os.environ.get("AI_GATEWAY_API_KEY") if connection == "vercel" else os.environ.get("TYPESAFE_API_KEY")
    if value:
        return value.strip()
    if sys.platform == "darwin":
        return _keychain_key(state_dir, "jev")
    try:
        return _unprotect_windows((Path(state_dir) / "jev.secret").read_bytes())
    except OSError:
        return None


def run_jev(config, state_dir, state, candidates):
    started = time.perf_counter()
    settings = config.get("jev") or {}
    connection = settings.get("connection", "typesafe")
    if connection == "vercel":
        endpoint = "https://ai-gateway.vercel.sh/v1/evaluate"
        model = "vmc/jev"
    elif connection == "typesafe":
        endpoint = "https://api.typesafe.ai/v1/systemone"
        model = "jev-latest"
    else:
        return {"engine": ENGINE_JEV, "status": "not_configured", "latency_ms": 0,
                "engine_failure": "unsupported_connection"}
    key = jev_key(state_dir, connection)
    if not key:
        return {"engine": ENGINE_JEV, "status": "not_configured", "latency_ms": 0}
    criteria = {name: "%s: %s" % (item["label"], item["description"]) for name, item in candidates.items()}
    has_previous_route = bool(state.get("previous_model") and state.get("previous_effort"))
    strategy_criteria = {
        "reassess": "La petición introduce un objetivo, alcance o complejidad que exige volver a elegir modelo y razonamiento.",
    }
    if has_previous_route:
        strategy_criteria["continue"] = "La petición es una continuación directa y la combinación anterior conserva calidad suficiente.",
    payload = {
        "model": model,
        "state": state,
        "questions": {
            "strategy": {"type": "choice", "instructions":
                "Decide si esta petición debe conservar la configuración anterior o volver a evaluarse. "
                "Continuar solo aplica a seguimientos directos sin un nuevo objetivo material.", "criteria": strategy_criteria},
            "route": {"type": "choice", "instructions":
                "Elige la combinación de modelo Codex y razonamiento más pequeña que mantenga buena calidad. "
                "Si hay adjuntos o una tarea visual, no infravalores la capacidad necesaria.", "criteria": criteria},
        },
    }
    try:
        response = _post_json(endpoint, payload,
                              {"Authorization": "Bearer " + key}, float(settings.get("timeout_seconds", 4)))
        answers = response.get("answers") or response.get("questions") or {}
        answer = (answers.get("route")
                  or response.get("route") or {})
        choice = answer.get("choice") if isinstance(answer, dict) else answer
        usage = engine_usage(response)
        if choice not in candidates:
            return {"engine": ENGINE_JEV, "status": "invalid", "engine_failure": "invalid_response",
                    "latency_ms": elapsed(started), "engine_model": payload["model"], **usage}
        strategy_answer = answers.get("strategy") if isinstance(answers, dict) else None
        strategy = strategy_answer.get("choice") if isinstance(strategy_answer, dict) else strategy_answer
        # Older JEV endpoints may not yet answer the extra question. Treat their
        # route as a re-evaluation rather than silently preserving a prior route.
        if strategy not in strategy_criteria:
            strategy = "reassess"
        confidence = answer.get("confidence") if isinstance(answer, dict) else None
        return {"engine": ENGINE_JEV, "status": "ok", "latency_ms": elapsed(started),
                "route": candidates[choice], "continuity_strategy": strategy,
                "confidence": number(confidence), "engine_model": payload["model"], **usage}
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, urllib.error.HTTPError, socket.timeout) as error:
        return {"engine": ENGINE_JEV, "status": "unavailable", "engine_failure": engine_failure(error),
                "latency_ms": elapsed(started), "engine_model": payload["model"]}


def elapsed(started):
    return int((time.perf_counter() - started) * 1000)


def number(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
