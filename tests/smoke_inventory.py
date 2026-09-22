"""Read-only native catalog integration; no model calls or conversation changes."""
import json
import sys
import time

from smoke_native import Client, ROOT


def main():
    client = Client([sys.executable, str(ROOT / "router.py"), "app-server"])
    try:
        client.call("initialize", {"clientInfo": {"name": "router_inventory_smoke", "version": "1.0"}})
        client.send({"method": "initialized", "params": {}})
        page = client.call("thread/list", {"limit": 1, "archived": False, "useStateDbOnly": True})
        thread = next(iter(page["data"]), None)
        if thread:
            client.call("thread/read", {"threadId": thread["id"], "includeTurns": False})
        snapshot_path = ROOT / "state" / ("status-%s.json" % client.p.pid)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if snapshot.get("inventory_synced_at"):
                break
            time.sleep(.2)
        else:
            raise AssertionError("Background catalog reconciliation did not complete")
        if thread:
            assert thread["id"] in snapshot["threads"], "Existing conversation disappeared"
            if thread.get("name"):
                assert snapshot["threads"][thread["id"]]["name"] == thread["name"]
        # Proves the periodic private responses did not leak into Desktop's stream.
        client.call("model/list", {})
        assert not any(str(m.get("id", "")).startswith("personal-router-inventory-")
                       for m in client.notifications)
        print("Native background catalog, current title, retained conversation and isolated replies: OK")
    finally:
        client.close()


if __name__ == "__main__":
    main()
