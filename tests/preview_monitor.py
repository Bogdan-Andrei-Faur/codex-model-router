"""Create isolated, labelled UI fixtures; never read or modify user telemetry."""
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.routing.routing import DEFAULT_ROUTES


def main():
    root = Path(tempfile.mkdtemp(prefix="codex-router-preview-"))
    state = root / "state"
    state.mkdir()
    (root / "config.local.json").write_text(json.dumps({"enabled": True, "routing_engine": "rules", "comparison_engines": [], "history_days": 90, "routes": DEFAULT_ROUTES}), encoding="utf-8")
    titles = ["Pulir la experiencia del monitor", "Corregir la validación del formulario", "Verificar las pruebas de regresión", "Revisar la arquitectura", "Traducir la documentación", "Auditar los permisos", "Investigar la sincronización", "Configurar el entorno"]
    categories = ["interface", "correction", "tests", "architecture", "text", "audit", "research", "configuration"]
    routes = list(DEFAULT_ROUTES.values())
    threads, events = {}, []
    now = time.time()
    for index, title in enumerate(titles):
        route = routes[index % 4]
        tid, did = "fixture-task-" + str(index), "fixture-decision-" + str(index)
        row = {"name": title, **route, "status": "active", "confirmation": "Aceptado por Codex", "updated": now-index,
               "decision_id": did, "agent_category": categories[index], "agent_confidence": "alta",
               "model_reason": "Alcance definido y verificable; se conserva la capacidad necesaria para la tarea.",
               "effort_reason": "El nivel permite comprobar las alternativas y validar el resultado."}
        if index == 0:
            row.update(model="gpt-6-astra", effort="xhigh")
        threads[tid] = row
        events += [{"event": "decision_created", "decision_id": did, "thread": tid, "title": title, "time": now-index*100-80, "model": row["model"], "effort": row["effort"], "model_reason": row["model_reason"], "effort_reason": row["effort_reason"]},
                   {"event": "decision_routed", "decision_id": did, "routing_engine": "rules", "time": now-index*100-79},
                   {"event": "decision_accepted", "decision_id": did, "time": now-index*100-78, "status": "inProgress"},
                   {"event": "decision_usage", "decision_id": did, "time": now-index*100-77, "inputTokens": 2400+index*80, "outputTokens": 320, "cachedInputTokens": 1800}]
    (root / "preview.json").write_text(json.dumps({"threads": threads}), encoding="utf-8")
    (state / "history.jsonl").write_text("\n".join(json.dumps(event) for event in events)+"\n", encoding="utf-8")
    print(root)


if __name__ == "__main__":
    main()
