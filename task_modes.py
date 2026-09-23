"""Persistent per-task control, shared by Windows/macOS monitors and bridge."""
import hashlib
import json
from pathlib import Path


def mode_path(state_dir, thread):
    if not isinstance(thread, str) or not thread or len(thread) > 200:
        raise ValueError("Invalid thread id")
    return Path(state_dir) / "task-modes" / (hashlib.sha256(thread.encode("utf-8")).hexdigest() + ".json")


def read_mode(state_dir, thread):
    try:
        data = json.loads(mode_path(state_dir, thread).read_text(encoding="utf-8"))
        return "automatic" if data.get("thread") == thread and data.get("mode") == "automatic" else "manual"
    except FileNotFoundError:
        return "automatic"
    except (OSError, ValueError, TypeError, AttributeError):
        # A damaged preference must not silently turn automatic routing back on.
        return "manual"
