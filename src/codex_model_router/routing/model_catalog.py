"""Reviewed OpenAI models, independently of routing policy and live-switch safety.

Availability and reasoning levels always come from the connected app-server.
Prices are dated reference estimates, never subscription billing measurements.
"""
from copy import deepcopy
import math

CATALOG_VERSION = "2026-09-30"
MODELS = {
    "gpt-6.1-sol": ("Sol 6.1", "sol", "complex"),
    "gpt-6-sol": ("Sol 6", "sol", "complex"),
    "gpt-6-luna": ("Luna 6", "luna", "simple"),
    "gpt-6-astra": ("Astra 6", "astra", "critical"),
    "gpt-5.6-sol": ("Sol 5.6", "sol", "complex"),
    "gpt-5.6-terra": ("Terra 5.6", "terra", "normal"),
    "gpt-5.6-luna": ("Luna 5.6", "luna", "simple"),
    "gpt-5.5": ("GPT-5.5", "legacy", "complex"),
}
LEGACY_ROUTES = {
    "simple": {"model": "gpt-5.6-luna", "effort": "low"},
    "normal": {"model": "gpt-5.6-terra", "effort": "medium"},
    "complex": {"model": "gpt-5.6-sol", "effort": "high"},
    "critical": {"model": "gpt-6-astra", "effort": "xhigh"},
}
DEFAULT_ROUTES = {
    "simple": {"model": "gpt-6-luna", "effort": "low"},
    "normal": {"model": "gpt-6.1-sol", "effort": "medium"},
    "complex": {"model": "gpt-6.1-sol", "effort": "high"},
    "critical": {"model": "gpt-6-astra", "effort": "xhigh"},
}
ALTERNATIVES = {
    "gpt-6-luna": ("gpt-5.6-luna",),
    "gpt-6.1-sol": ("gpt-6-sol", "gpt-5.6-sol"),
    "gpt-6-sol": ("gpt-5.6-sol",),
}


def model_label(model):
    return MODELS.get(model, (model,))[0]


def migrate_config(config):
    """Upgrade only untouched old defaults. Explicitly versioned/custom maps win."""
    result = deepcopy(config)
    if result.get("model_catalog_version") is None and result.get("routes") == LEGACY_ROUTES:
        result["routes"] = deepcopy(DEFAULT_ROUTES)
        result["model_catalog_version"] = CATALOG_VERSION
    return result


def available_routes(routes, catalog):
    result = deepcopy(routes)
    for route in result.values():
        model = route.get("model")
        if model not in catalog:
            route["model"] = next((m for m in ALTERNATIVES.get(model, ()) if m in catalog), model)
    return result


# Standard short-context USD input/cache-read/cache-write/output per million.
API_RATES = {
    "gpt-6.1-sol": (2, .1, 2.5, 10), "gpt-6-sol": (2, .2, 2.5, 10),
    "gpt-6-luna": (.1, .01, .125, .5), "gpt-6-astra": (10, 1, 12.5, 50),
    "gpt-5.6-sol": (4, .4, 5, 20), "gpt-5.6-terra": (2, .2, 2.5, 12),
    "gpt-5.6-luna": (.2, .02, .25, 1.2), "gpt-5.5": (5, .5, None, 30),
}
CODEX_RATES = {
    "gpt-6.1-sol": (50, 2.5, 250), "gpt-6-sol": (50, 5, 250),
    "gpt-6-luna": (2.5, .25, 12.5), "gpt-6-astra": (250, 25, 1250),
    "gpt-5.6-sol": (100, 10, 500), "gpt-5.6-terra": (50, 5, 300),
    "gpt-5.6-luna": (5, .5, 30), "gpt-5.5": (125, 12.5, 750),
}


def estimate_standard_usage(model, metrics):
    """Only complete observed usage; output already includes reasoning tokens.

Service tier is not currently observed: always Standard-equivalent, never actual
cost. Cache reads/writes are subsets of input. Missing cache data is unknown.
"""
    keys = ("inference_input_tokens", "inference_cached_tokens", "inference_output_tokens")
    values = [metrics.get(key) for key in keys]
    write = metrics.get("inference_cache_write_tokens", 0)
    if model not in API_RATES or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in [*values, write]):
        return {}
    total, cached, output = values
    if cached + write > total:
        return {}
    # Long-context thresholds/rates can differ by product. Do not extrapolate.
    if total > 272000:
        return {}
    inp, read, cache_write, out = API_RATES[model]
    if write and cache_write is None:
        return {}
    credits_in, credits_cache, credits_out = CODEX_RATES[model]
    result = {
        "estimated_codex_standard_credits": round(((total-cached)*credits_in + cached*credits_cache + output*credits_out)/1e6, 8),
        "estimate_basis": "standard_equivalent_not_billed",
        "estimate_rates_version": CATALOG_VERSION,
    }
    if "inference_cache_write_tokens" in metrics or model == "gpt-5.5":
        result["estimated_api_standard_usd"] = round(((total-cached-write)*inp + cached*read + write*(cache_write or 0) + output*out)/1e6, 8)
    return result
