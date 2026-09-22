"""Optional decision engines for the personal Codex router.

The engines receive a single, transient routing state. They never write prompt
text, attachment contents, credentials or model output to disk. Every failure
returns control to the deterministic local policy.
"""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request


ENGINE_RULES = "rules"
ENGINE_JEV = "jev"
ENGINE_PROVIDER = "provider"
# Kept only to interpret historical local configuration from the first release.
ENGINE_OLLAMA = "ollama"
ENGINES = (ENGINE_RULES, ENGINE_JEV, ENGINE_PROVIDER, ENGINE_OLLAMA)


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


def inline_images(items):
    """Extract only data-URI images already carried by Codex; never read local paths."""
    images = []
    for item in items:
        if not isinstance(item, dict):
            continue
        values = [item.get("image_url"), item.get("url"), item.get("data")]
        for value in values:
            if isinstance(value, dict):
                value = value.get("url")
            if not isinstance(value, str) or not value.startswith("data:image/") or ";base64," not in value:
                continue
            encoded = value.split(";base64,", 1)[1]
            # Do not forward malformed arbitrary strings to an external service.
            try:
                base64.b64decode(encoded, validate=True)
            except (ValueError, base64.binascii.Error):
                continue
            images.append(encoded)
            break
    return images


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


def jev_key(state_dir):
    """Environment variables are useful for development; production key stays DPAPI-protected."""
    value = os.environ.get("PERSONAL_CODEX_JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if value:
        return value.strip()
    try:
        return _unprotect_windows((Path(state_dir) / "jev.secret").read_bytes())
    except OSError:
        return None


def provider_key(state_dir, provider_id):
    """Provider keys use Windows DPAPI and never enter configuration or telemetry."""
    if provider_id == "ollama":
        value = os.environ.get("OLLAMA_API_KEY")
        if value:
            return value.strip()
    try:
        return _unprotect_windows((Path(state_dir) / (provider_id + ".secret")).read_bytes())
    except OSError:
        return None


def run_jev(config, state_dir, state, candidates):
    started = time.perf_counter()
    key = jev_key(state_dir)
    if not key:
        return {"engine": ENGINE_JEV, "status": "not_configured", "latency_ms": 0}
    settings = config.get("jev") or {}
    criteria = {name: "%s: %s" % (item["label"], item["description"]) for name, item in candidates.items()}
    payload = {
        "model": settings.get("model", "jev-latest"),
        "state": state,
        "questions": {"route": {"type": "choice", "instructions":
            "Elige la combinación de modelo Codex y razonamiento más pequeña que mantenga buena calidad. "
            "Si hay adjuntos o una tarea visual, no infravalores la capacidad necesaria.", "criteria": criteria}},
    }
    try:
        response = _post_json(settings.get("endpoint", "https://api.typesafe.ai/v1/systemone"), payload,
                              {"Authorization": "Bearer " + key}, float(settings.get("timeout_seconds", 4)))
        answer = ((response.get("answers") or {}).get("route") or (response.get("questions") or {}).get("route")
                  or response.get("route") or {})
        choice = answer.get("choice") if isinstance(answer, dict) else answer
        if choice not in candidates:
            return {"engine": ENGINE_JEV, "status": "invalid", "latency_ms": elapsed(started)}
        confidence = answer.get("confidence") if isinstance(answer, dict) else None
        return {"engine": ENGINE_JEV, "status": "ok", "latency_ms": elapsed(started),
                "route": candidates[choice], "confidence": number(confidence), "engine_model": payload["model"]}
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, urllib.error.HTTPError):
        return {"engine": ENGINE_JEV, "status": "unavailable", "latency_ms": elapsed(started)}


def run_provider(config, state_dir, state, candidates, images=None):
    started = time.perf_counter()
    # Old installations used an `ollama` block. Read it once as a safe migration
    # path, while all new configuration lives under `provider`.
    settings = config.get("provider") or config.get("ollama") or {}
    provider_id = settings.get("id", "ollama")
    if provider_id != "ollama":
        return {"engine": ENGINE_PROVIDER, "status": "not_configured", "latency_ms": 0,
                "engine_model": provider_id}
    connection = settings.get("connection", "local")
    key = provider_key(state_dir, provider_id) if connection == "api_key" else None
    if connection == "api_key" and not key:
        return {"engine": ENGINE_PROVIDER, "status": "not_configured", "latency_ms": 0,
                "engine_model": "Ollama"}
    labels = "\n".join("%s — %s" % (name, item["label"]) for name, item in candidates.items())
    prompt = ("Clasifica esta petición para elegir Codex. Responde únicamente con una de estas claves, sin explicación:\n" +
              labels + "\n\nEstado:\n" + json.dumps(state, ensure_ascii=False, separators=(",", ":")))
    user = {"role": "user", "content": prompt}
    if images:
        user["images"] = images
    payload = {"model": settings.get("model", "glm-5.3-flash:cloud"), "stream": False, "think": False,
               "messages": [{"role": "system", "content": "Eres un clasificador de rutas. Sigue exactamente el formato solicitado."},
                            user], "options": {"temperature": 0}}
    try:
        endpoint = settings.get("endpoint") or ("https://ollama.com/api/chat" if connection == "api_key" else "http://127.0.0.1:11434/api/chat")
        headers = {"Authorization": "Bearer " + key} if key else None
        response = _post_json(endpoint, payload, headers=headers, timeout=float(settings.get("timeout_seconds", 6)))
        content = str((response.get("message") or {}).get("content") or "").strip().lower()
        found = [key for key in candidates if re.search(r"\b" + re.escape(key.lower()) + r"\b", content)]
        if len(found) != 1:
            return {"engine": ENGINE_PROVIDER, "status": "invalid", "latency_ms": elapsed(started), "engine_model": "Ollama · " + payload["model"]}
        return {"engine": ENGINE_PROVIDER, "status": "ok", "latency_ms": elapsed(started),
                "route": candidates[found[0]], "engine_model": "Ollama · " + payload["model"]}
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, urllib.error.HTTPError):
        return {"engine": ENGINE_PROVIDER, "status": "unavailable", "latency_ms": elapsed(started), "engine_model": "Ollama · " + payload["model"]}


def run_ollama(config, state, candidates, images=None):
    """Compatibility entry point for integrations using the pre-provider API."""
    return run_provider(config, "", state, candidates, images)


def elapsed(started):
    return int((time.perf_counter() - started) * 1000)


def number(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
