"""Cross-process journal writes and independent privacy-safe task state."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid

_locks = {}
_guard = threading.Lock()


@contextmanager
def file_lock(path, timeout=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _guard:
        local = _locks.setdefault(str(path.resolve()), threading.RLock())
    with local, path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("state_lock_timeout")
                time.sleep(.02)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def read_records(path):
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        yield value
                except (ValueError, TypeError):
                    continue  # One torn record must not stop replay of later data.
    except FileNotFoundError:
        return


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def append_record(state, record):
    state = Path(state)
    with file_lock(state / "history.lock"):
        history = state / "history.jsonl"
        # A killed writer can leave a partial final line. Isolate it before the
        # next append so recovery can still read the next valid record.
        with history.open("a+b") as stream:
            stream.seek(0, 2)
            if stream.tell():
                stream.seek(-1, 2)
                if stream.read(1) != b"\n":
                    stream.write(b"\n")
            stream.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            stream.flush()
        if os.name != "nt":
            history.chmod(0o600)


def compact_history(state, days, now=None):
    state = Path(state)
    if days <= 0:
        return  # Siempre means no event-count cap.
    now = time.time() if now is None else now
    # Older running bridges do not participate in the lock. Defer destructive
    # retention until they exit, including during an in-place product upgrade.
    for status in state.glob("status-*.json"):
        try:
            data = json.loads(status.read_text(encoding="utf-8"))
            if now - float(data.get("heartbeat", 0)) < 15 and data.get("storage_schema", 0) < 3:
                return
        except (OSError, ValueError, TypeError):
            continue
    history = state / "history.jsonl"
    cutoff = now - days * 86400
    with file_lock(state / "history.lock"):
        rows = list(read_records(history))
        recent = {r.get("decision_id") for r in rows if isinstance(r.get("time"), (int, float)) and r["time"] >= cutoff}
        kept = [r for r in rows if (r.get("decision_id") in recent if r.get("decision_id") else isinstance(r.get("time"), (int, float)) and r.get("time", 0) >= cutoff)]
        temporary = state / ("history-" + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                for row in kept:
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, history)
        finally:
            temporary.unlink(missing_ok=True)


def persist_task(state, thread, row, only_if_missing=False):
    if not thread:
        return
    key = hashlib.sha256(thread.encode()).hexdigest()
    fields = {k: row[k] for k in ("agent_category", "agent_confidence", "task_contract", "task_floor") if k in row}
    with file_lock(Path(state) / "workloads.lock"):
        path = Path(state) / "workloads" / (key + ".json")
        if only_if_missing and path.exists():
            return
        atomic_json(path, {"thread": thread, **fields})


def recover_tasks(state):
    state = Path(state)
    rows = {}
    for record in read_records(state / "history.jsonl"):
        thread = record.get("thread")
        if not isinstance(thread, str):
            continue
        row = rows.setdefault(thread, {})
        for key in ("agent_category", "agent_confidence"):
            if key in record:
                row[key] = record[key]
        if record.get("event") == "task_context":
            floor = record.get("task_floor")
            if floor in ("normal", "complex", "critical"):
                row["task_floor"] = floor
            elif floor in ("cleared", "none"):
                row.pop("task_floor", None)
    for path in (state / "workloads").glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            thread = row.pop("thread")
            rows[thread] = row
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return rows
