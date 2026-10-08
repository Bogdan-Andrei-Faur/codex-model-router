"""Check routing boundaries; --live evaluates synthetic prompts with configured JEV.

No Codex inference, user tasks, prompt logs, state changes or raw provider output.
Live mode consumes a small amount of the configured classifier provider quota.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from codex_model_router.routing.decision_engines import build_state, candidate_routes, run_jev
from codex_model_router.routing.model_catalog import migrate_config, available_routes
from codex_model_router.routing.routing import DEFAULT_ROUTES, EFFORTS, select_route_details


CASES = (
    ("confirmation", "Parece que ahora si esta funcionando", "critical", "max"),
    ("status", "Comprueba cuantas solicitudes de telemetria han llegado", "critical", "max"),
    ("continue_work", "Adelante, impleméntalo", "critical", "max"),
    ("ambiguous", "Tengo una duda sobre esto", "critical", "max"),
    ("high_risk", "Audita exhaustivamente la autenticación y los riesgos de pérdida de datos", None, None),
    ("retry", "Sigue fallando", "critical", "xhigh"),
)


def live_catalog(state_dir):
    # Historical snapshots cannot establish availability after a Desktop update.
    from smoke_native import Client
    client = Client()
    try:
        client.call("initialize", {"clientInfo": {"name": "classifier_catalog_probe", "version": "1.0"}})
        client.send({"method": "initialized", "params": {}})
        rows = client.call("model/list", {})["data"]
        return {m["model"]: {e["reasoningEffort"] for e in m.get("supportedReasoningEfforts", [])}
                for m in rows if not m.get("hidden")}
    finally:
        client.close()
        client.temp.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--case", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    config = json.loads((ROOT / "config.local.json").read_text(encoding="utf-8-sig")) if args.live else {}
    config = migrate_config(config)
    routes = config.get("routes", DEFAULT_ROUTES)
    catalog = {route["model"]: set(EFFORTS) for route in routes.values()}
    state_dir = Path(os.environ.get("PERSONAL_CODEX_ROUTER_STATE", ROOT / "state"))
    if args.live:
        catalog = live_catalog(state_dir)
        routes = available_routes(routes, catalog)
    failures = 0
    for name, prompt, previous, effort in CASES:
        if args.case and name != args.case:
            continue
        _, policy = select_route_details(prompt, routes, previous, effort)
        candidates = candidate_routes(routes, catalog, policy)
        report = {"case": name, "request_kind": policy["request_kind"], "quality_floor": policy["quality_floor"],
                  "max_effort_allowed": policy["max_effort_allowed"], "candidates": sorted(candidates)}
        if args.live:
            state = build_state(prompt, {"present": False, "count": 0, "images": 0, "types": []},
                                routes[previous]["model"] if previous else None, effort, policy["signal"] == "retry")
            state.update({key: policy[key] for key in ("request_kind", "quality_floor", "max_effort_allowed")})
            result = run_jev(config, state_dir, state, candidates)
            report.update({key: result.get(key) for key in ("status", "continuity_strategy", "confidence", "latency_ms", "engine_failure")})
            route = result.get("route") or {}
            report.update(model=route.get("model"), effort=route.get("effort"))
            valid = any(route.get("model") == item["model"] and route.get("effort") == item["effort"] for item in candidates.values())
            report["within_policy"] = valid
            failures += result.get("status") != "ok" or not valid
        else:
            expected_floor = {"continue_work": "complex", "ambiguous": "complex", "high_risk": "critical", "retry": "critical"}.get(name)
            valid = policy.get("quality_floor") == expected_floor
            if name in ("confirmation", "status"):
                valid &= all(item["tier"] in ("simple", "normal") and item["effort"] in ("low", "medium") for item in candidates.values())
            report["within_policy"] = bool(valid)
            failures += not valid
        print(json.dumps(report, ensure_ascii=False), flush=True)
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
