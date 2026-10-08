"""Cross-process journal writes and independent privacy-safe task state."""
from contextlib import contextmanager
import hashlib
import json
import os
import stat
from pathlib import Path
import threading
import time
import uuid

_locks = {}
_guard = threading.Lock()


def private_directory(path):
    """Seal an owned state directory without following a replacement link."""
    path = Path(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe_state_directory")
    if os.name != "nt":
        if info.st_uid != os.getuid():
            raise OSError("unowned_state_directory")
        path.chmod(0o700)
    return path


def private_open(path, mode="w", **kwargs):
    """Create owner-only files; restrict existing descriptors before any write."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    if mode == "a+b":
        flags |= os.O_RDWR | os.O_APPEND
    elif mode in ("w", "wb", "x", "xb"):
        flags |= os.O_WRONLY
        if mode.startswith("x"):
            flags |= os.O_EXCL
    else:
        raise ValueError("unsupported_private_open_mode")
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError("unsafe_state_file")
        if os.name != "nt":
            if info.st_uid != os.getuid():
                raise OSError("unowned_state_file")
            os.fchmod(fd, 0o600)
        if mode.startswith("w"):
            os.ftruncate(fd, 0)
        stream = os.fdopen(fd, mode, **kwargs)
    except BaseException:
        os.close(fd)
        raise
    return stream


@contextmanager
def file_lock(path, timeout=10):
    path = Path(path)
    # Generic locks also live beside migration destinations. Never change the
    # permissions of a caller's existing shared parent or its siblings.
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _guard:
        local = _locks.setdefault(str(path.resolve()), threading.RLock())
    with local, private_open(path, "a+b") as stream:
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
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with private_open(temporary, "x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append_jsonl(state, filename, lockname, record):
    state = private_directory(state)
    with file_lock(state / lockname):
        history = state / filename
        # A killed writer can leave a partial final line. Isolate it before the
        # next append so recovery can still read the next valid record.
        with private_open(history, "a+b") as stream:
            stream.seek(0, 2)
            if stream.tell():
                stream.seek(-1, 2)
                if stream.read(1) != b"\n":
                    stream.write(b"\n")
            stream.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            stream.flush()


def append_record(state, record):
    _append_jsonl(state, "history.jsonl", "history.lock", record)


def append_prompt_record(state, record):
    """Append the explicitly enabled private routing dataset."""
    _append_jsonl(state, "prompts.jsonl", "prompts.lock", record)


def compact_history(state, days, now=None):
    state = Path(state)
    if days <= 0:
        return  # Siempre means no event-count cap.
    private_directory(state)
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
            with private_open(temporary, "x", encoding="utf-8", newline="\n") as stream:
                for row in kept:
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, history)
        finally:
            temporary.unlink(missing_ok=True)


def compact_prompt_history(state, days, now=None):
    """Apply the normal history retention window to the private prompt file."""
    if days <= 0:
        return
    state = private_directory(state)
    cutoff = (time.time() if now is None else now) - days * 86400
    prompts = state / "prompts.jsonl"
    with file_lock(state / "prompts.lock"):
        rows = [row for row in read_records(prompts)
                if isinstance(row.get("time"), (int, float)) and row["time"] >= cutoff]
        temporary = state / ("prompts-" + uuid.uuid4().hex + ".tmp")
        try:
            with private_open(temporary, "x", encoding="utf-8", newline="\n") as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, prompts)
        finally:
            temporary.unlink(missing_ok=True)


def persist_task(state, thread, row, only_if_missing=False):
    if not thread:
        return
    state = private_directory(state)
    key = hashlib.sha256(thread.encode()).hexdigest()
    fields = {k: row[k] for k in ("agent_category", "agent_confidence", "task_contract", "task_floor",
                                  "pending_phase_floor", "pending_phase_name", "pending_phase_id", "candidate_contract") if k in row}
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
