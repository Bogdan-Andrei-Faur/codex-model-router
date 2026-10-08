"""Read-only app-server catalog reconciliation for the monitor, not routing state."""
import time
import uuid


def thread_metadata(thread, previous=None, request=None, method=None):
    """Separate explicit user side chats from internal ephemeral forks.

    forkedFromId is ancestry, not evidence that a fork is user-facing: Desktop
    also forks conversations to generate titles. Never inspect instructions.
    Sparse notifications must not erase metadata captured from the fork ACK.
    """
    previous, request = previous or {}, request or {}
    def identifier(value):
        return value if isinstance(value, str) and value else None
    parent = identifier(thread.get("parentThreadId")) or previous.get("parent")
    fork = (identifier(thread.get("forkedFromId")) or
            (identifier(request.get("threadId")) if method == "thread/fork" else None) or
            previous.get("forked_from"))
    source = thread.get("threadSource") or request.get("threadSource") or previous.get("thread_source")
    source = "user" if source == "user" else "internal" if source else None
    ephemeral = thread.get("ephemeral", request.get("ephemeral", previous.get("ephemeral", False))) is True
    return {"parent": parent, "forked_from": fork, "thread_source": source,
            "ephemeral": ephemeral, "side_chat": bool(ephemeral and fork and source == "user")}


class ThreadInventory:
    INTERVAL = 15
    TIMEOUT = 30

    def __init__(self):
        self.ready = False
        self.prefix = "personal-router-inventory-" + uuid.uuid4().hex + "-"
        self.request_id = None
        self.started = 0
        self.last_attempt = -self.INTERVAL
        self.catalog = None
        self.pages = {}
        self.cursors = set()
        self.hidden = set()
        self.names = {}
        self.observed_at_start = set()
        self.catalog_observed = set()
        self.synced_at = None

    def _request(self, cursor=None):
        self.request_id = self.prefix + uuid.uuid4().hex
        params = {"limit": 100, "archived": False, "useStateDbOnly": True,
                  "sourceKinds": ["cli", "vscode", "exec", "appServer", "subAgent", "unknown"]}
        if cursor:
            params["cursor"] = cursor
        return {"id": self.request_id, "method": "thread/list", "params": params}

    def poll(self, observed, now=None):
        now = time.monotonic() if now is None else now
        if not self.ready:
            return None
        if self.request_id and now - self.started < self.TIMEOUT:
            return None
        if now - self.last_attempt < self.INTERVAL:
            return None
        self.started = self.last_attempt = now
        self.pages, self.cursors = {}, set()
        self.observed_at_start = set(observed)
        return self._request()

    def consume(self, message):
        """Return (owned response, next page); publish only complete valid scans."""
        rid = message.get("id")
        if "method" in message or not isinstance(rid, str) or not rid.startswith(self.prefix):
            return False, None
        if rid != self.request_id:
            return True, None  # Late reply after timeout or a lifecycle change.
        self.request_id = None
        result = message.get("result")
        if ("error" in message or not isinstance(result, dict) or not isinstance(result.get("data"), list)
                or "nextCursor" not in result):
            return True, None
        for thread in result["data"]:
            if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
                return True, None
            # Never retain previews, messages, paths, or full server responses.
            self.pages[thread["id"]] = {"name": thread.get("name") or thread.get("agentNickname"),
                                        "parent": thread.get("parentThreadId")}
        cursor = result.get("nextCursor")
        if cursor:
            if not isinstance(cursor, str) or cursor in self.cursors or len(self.cursors) >= 1000:
                return True, None
            self.cursors.add(cursor)
            return True, self._request(cursor)
        self.catalog = self.pages
        self.catalog_observed = self.observed_at_start
        self.synced_at = time.time()
        self.hidden.difference_update(self.catalog)
        self.names = {tid: row["name"] for tid, row in self.catalog.items() if row.get("name")}
        return True, None

    def notification(self, method, params):
        tid = params.get("threadId")
        if not tid:
            return
        if method in ("thread/archived", "thread/deleted"):
            self.hidden.add(tid)
        elif method == "thread/unarchived":
            self.hidden.discard(tid)
            if self.catalog is not None:
                self.catalog[tid] = {}
        elif method == "thread/name/updated":
            name = params.get("threadName") or params.get("name")
            if isinstance(name, str) and name:
                self.names[tid] = name
        else:
            return
        # Do not let an older in-flight page undo a rename/archive notification.
        self.request_id = None
        self.last_attempt = -self.INTERVAL

    def visible(self, threads):
        rows = {}
        for tid, row in threads.items():
            if tid in self.hidden or row.get("parent") in self.hidden:
                continue
            working = row.get("status") in ("active", "inProgress", "running", "pending")
            if row.get("ephemeral"):
                # Codex also creates in-memory root forks for internal work such
                # as title generation. They are not user conversations. Real
                # collaboration agents acquire a parent. Explicit user forks
                # are side chats. Both are visible only while working.
                if not (row.get("parent") or row.get("side_chat")) or not working:
                    continue
            if self.catalog is not None and tid not in self.catalog and tid in self.catalog_observed:
                # Ephemeral agents have no persistent catalog entry while working.
                if not (working and (row.get("ephemeral") or row.get("parent") in self.catalog)):
                    continue
            rows[tid] = {**row}
            if tid in self.names:
                rows[tid]["name"] = self.names[tid]
            if row.get("side_chat"):
                # Status files are persistent; never put a temporary chat title
                # in them, even if Desktop sends thread/name/updated later.
                rows[tid]["name"] = "Chat lateral"
        return rows

    def agents(self, threads):
        """Monitor-only non-archived catalog, with no inferred routing settings."""
        rows = self.visible(threads)
        for tid, metadata in (self.catalog or {}).items():
            if tid in rows or tid in self.hidden or metadata.get("parent") in self.hidden:
                continue
            # Do not resurrect suppressed internal/ephemeral rows from the catalog.
            if tid in threads and threads[tid].get("ephemeral"):
                continue
            rows[tid] = {"name": self.names.get(tid) or metadata.get("name") or "Agente",
                         "parent": metadata.get("parent"), "status": "idle",
                         "catalog_only": True, "updated": 0}
        return rows
