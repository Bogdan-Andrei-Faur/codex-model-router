"""Bounded routing workers; control messages never wait for a classifier."""
import json
import queue
import threading
from task_modes import read_mode


class Dispatcher:
    def __init__(self, router, send_native, send_client, workers=2, capacity=16):
        self.router, self.send_native, self.send_client = router, send_native, send_client
        self.queue = queue.Queue(capacity)
        self.pending = {}
        self.lock = threading.RLock()
        self.closed = False
        for _ in range(workers):
            threading.Thread(target=self.work, daemon=True).start()

    def reply(self, request, error=None):
        if "id" not in request:
            return
        value = {"id": request["id"]}
        value.update({"error": {"code": -32800, "message": error}} if error else {"result": {}})
        self.send_client((json.dumps(value) + "\n").encode())

    def submit(self, raw):
        try:
            message = json.loads(raw)
            params = message.get("params") or {}
            method, tid = message.get("method"), params.get("threadId")
        except (ValueError, AttributeError):
            self.send_native(self.router.client_line(raw))
            return
        if method in ("turn/start", "turn/interrupt") and not isinstance(tid, str):
            # Preserve malformed protocol input for the native validator; it
            # must not terminate the stdin worker before Desktop gets an error.
            self.send_native(raw)
            return
        with self.lock:
            if method == "turn/interrupt" and tid in self.pending:
                job = self.pending[tid]
                if job["cancelled"]:
                    self.reply(message)
                    return
                job["cancelled"] = True
                self.reply(job["message"], "Turn cancelled before submission")
                self.reply(message)
                return
            if method != "turn/start" or not tid:
                self.send_native(self.router.client_line(raw))
                return
            if tid in self.pending:
                self.reply(message, "A turn is already being prepared for this task")
                return
            job = {"raw": raw, "message": message, "thread": tid, "cancelled": False,
                   "mode": read_mode(self.router.state_dir, tid)}
            self.pending[tid] = job
            try:
                self.queue.put_nowait(job)
            except queue.Full:
                self.pending.pop(tid, None)
                self.reply(message, "Router is busy; retry this turn")

    def work(self):
        while True:
            job = self.queue.get()
            try:
                if job["cancelled"] or self.closed:
                    with self.lock:
                        if self.pending.get(job["thread"]) is job:
                            self.pending.pop(job["thread"], None)
                    continue
                routed = self.router.client_line(job["raw"], job["mode"])
                with self.lock:
                    if job["cancelled"] or self.closed:
                        self.router.cancel_prepared(job["message"])
                    else:
                        self.send_native(routed)
                    if self.pending.get(job["thread"]) is job:
                        self.pending.pop(job["thread"], None)
            except (OSError, ValueError):
                self.router.cancel_prepared(job["message"])
                with self.lock:
                    if self.pending.get(job["thread"]) is job:
                        self.pending.pop(job["thread"], None)
            finally:
                self.queue.task_done()

    def close(self):
        with self.lock:
            self.closed = True
            for job in self.pending.values():
                job["cancelled"] = True
