"""Recover explicitly selected legacy snapshots into a separate persistent journal.

Never reads prompts or writes the live router journal. Deterministic decision IDs
make reruns idempotent; missing effort explanations and usage stay unknown.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from codex_model_router.paths import resource_root
import uuid
from codex_model_router.storage.state_store import private_open


def recover_records(snapshot):
    records = []
    pending = {}
    occurrences = Counter()
    for event in snapshot.get("events", []):
        kind = event.get("event")
        thread = event.get("thread")
        if kind == "turn_accepted" and thread:
            # Modern records already have native decision IDs and their own journal.
            if event.get("decision_id"):
                pending.pop(thread, None)
                continue
            try:
                timestamp = datetime.fromisoformat(event["time"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError, TypeError):
                continue
            key = json.dumps([snapshot.get("pid"), event.get("time"), thread,
                              event.get("model"), event.get("effort")], separators=(",", ":"))
            occurrences[key] += 1
            identity = hashlib.sha256((key + ":" + str(occurrences[key])).encode()).hexdigest()
            title = snapshot.get("threads", {}).get(thread, {}).get("name") or thread[:8]
            record = {"schema": 1, "event": "decision_recovered", "decision_id": "recovered-" + identity,
                      "time": timestamp, "time_iso": event["time"], "thread": thread, "title": title,
                      "model": event.get("model"), "effort": event.get("effort"),
                      "model_reason": event.get("reason") or "Motivo no conservado en el registro anterior.",
                      "effort_reason": "El registro anterior no conservó una explicación separada del razonamiento.",
                      "source": "recovered", "status": "unknown"}
            records.append(record)
            pending[thread] = record
        elif kind == "turn_completed" and thread in pending:
            # Completion was observed; success/failure and duration were not logged.
            pending.pop(thread)["status"] = "finished"
    return records


def recover(source, destination):
    snapshot = json.loads(Path(source).read_text(encoding="utf-8"))
    destination = Path(destination)
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    ids = {json.loads(line)["decision_id"] for line in existing.splitlines() if line.strip()}
    records = [record for record in recover_records(snapshot) if record["decision_id"] not in ids]
    if records:
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = existing + ("\n" if existing and not existing.endswith("\n") else "")
        text += "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)
        temp = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with private_open(temp, "x", encoding="utf-8") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--destination", type=Path,
                        default=resource_root() / "state" / "history.recovered.jsonl")
    args = parser.parse_args()
    print("Recovered decisions:", recover(args.source, args.destination))
