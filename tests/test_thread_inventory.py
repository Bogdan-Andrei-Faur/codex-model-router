import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thread_inventory import ThreadInventory
from router import Router


class ThreadInventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = ThreadInventory()
        self.inventory.ready = True
        self.rows = {"kept": {"name": "Old name", "model": "gpt-6-astra", "status": "idle"},
                     "deleted": {"name": "01a0c88e", "status": "idle"}}

    def reply(self, request, data, cursor=None):
        return self.inventory.consume({"id": request["id"], "result": {"data": data, "nextCursor": cursor}})

    def test_full_catalog_hydrates_title_and_filters_only_monitor_view(self):
        req = self.inventory.poll(self.rows, now=0)
        self.reply(req, [{"id": "kept", "name": "Current title", "preview": "PRIVATE CONTENT"}])
        visible = self.inventory.visible(self.rows)
        self.assertEqual(set(visible), {"kept"})
        self.assertEqual(visible["kept"]["name"], "Current title")
        self.assertEqual(visible["kept"]["model"], "gpt-6-astra")
        self.assertEqual(self.rows["kept"]["name"], "Old name")
        self.assertIn("deleted", self.rows)
        self.assertNotIn("PRIVATE CONTENT", json.dumps(self.inventory.catalog))

    def test_agents_include_unobserved_catalog_without_mutating_home_or_routing(self):
        req = self.inventory.poll(self.rows, now=0)
        self.reply(req, [{"id": "kept", "name": "Current"},
                         {"id": "unseen", "name": "Inactive catalog task", "preview": "PRIVATE"}])
        agents = self.inventory.agents(self.rows)
        self.assertEqual(set(agents), {"kept", "unseen"})
        self.assertTrue(agents["unseen"]["catalog_only"])
        self.assertNotIn("model", agents["unseen"])
        self.assertNotIn("PRIVATE", json.dumps(agents))
        self.assertEqual(set(self.inventory.visible(self.rows)), {"kept"})
        self.assertNotIn("unseen", self.rows)
        self.inventory.notification("thread/archived", {"threadId": "unseen"})
        self.assertNotIn("unseen", self.inventory.agents(self.rows))
        self.inventory.notification("thread/unarchived", {"threadId": "unseen"})
        self.assertIn("unseen", self.inventory.agents(self.rows))

    def test_all_pages_required_and_failed_page_keeps_last_good_snapshot(self):
        req = self.inventory.poll(self.rows, now=0)
        owned, next_page = self.reply(req, [{"id": "kept", "name": "New"}], "page2")
        self.assertTrue(owned)
        self.assertEqual(set(self.inventory.visible(self.rows)), set(self.rows))
        self.reply(next_page, [{"id": "deleted", "name": "Actually exists"}])
        req = self.inventory.poll(self.rows, now=16)
        _, next_page = self.reply(req, [], "page2")
        self.inventory.consume({"id": next_page["id"], "error": {"code": -1}})
        self.assertEqual(set(self.inventory.visible(self.rows)), set(self.rows))
        self.assertEqual(self.inventory.visible(self.rows)["deleted"]["name"], "Actually exists")

    def test_archive_delete_rename_and_restore_survive_late_pages(self):
        req = self.inventory.poll(self.rows, now=0)
        self.inventory.notification("thread/name/updated", {"threadId": "kept", "threadName": "Renamed"})
        self.inventory.notification("thread/archived", {"threadId": "deleted"})
        self.reply(req, [{"id": "deleted"}, {"id": "kept", "name": "Stale"}])
        self.assertEqual(set(self.inventory.visible(self.rows)), {"kept"})
        self.assertEqual(self.inventory.visible(self.rows)["kept"]["name"], "Renamed")
        self.inventory.notification("thread/unarchived", {"threadId": "deleted"})
        self.assertIn("deleted", self.inventory.visible(self.rows))
        self.inventory.notification("thread/deleted", {"threadId": "deleted"})
        self.assertNotIn("deleted", self.inventory.visible(self.rows))

    def test_timeout_retries_and_late_reply_is_hidden(self):
        first = self.inventory.poll(self.rows, now=0)
        self.assertIsNone(self.inventory.poll(self.rows, now=16))
        second = self.inventory.poll(self.rows, now=31)
        self.reply(first, [])
        self.assertIsNone(self.inventory.catalog)
        self.reply(second, [{"id": "kept"}])
        self.assertEqual(set(self.inventory.visible(self.rows)), {"kept"})
        self.assertEqual(self.inventory.consume({"id": "user", "result": {}}), (False, None))

    def test_new_and_working_ephemeral_agents_are_not_hidden_mid_scan(self):
        self.rows["child"] = {"parent": "kept", "status": "inProgress"}
        self.rows["internal"] = {"ephemeral": True, "status": "active"}
        self.rows["ephemeral_child"] = {"ephemeral": True, "parent": "kept", "status": "active"}
        req = self.inventory.poll(self.rows, now=0)
        self.rows["new"] = {"name": "Just created"}
        self.reply(req, [{"id": "kept"}])
        self.assertEqual(set(self.inventory.visible(self.rows)), {"kept", "child", "ephemeral_child", "new"})
        self.rows["child"]["status"] = "completed"
        self.rows["ephemeral_child"]["status"] = "idle"
        self.assertEqual(set(self.inventory.visible(self.rows)), {"kept", "new"})
        req = self.inventory.poll(self.rows, now=16)
        self.inventory.consume({"id": req["id"], "error": {"code": -1}})
        self.assertIn("new", self.inventory.visible(self.rows))

    def test_no_poll_before_initialized_and_no_incomplete_or_looping_catalog(self):
        self.inventory.ready = False
        self.assertIsNone(self.inventory.poll(self.rows, now=0))
        self.inventory.ready = True
        req = self.inventory.poll(self.rows, now=0)
        self.inventory.consume({"id": req["id"], "result": {"data": []}})
        self.assertIsNone(self.inventory.catalog)
        req = self.inventory.poll(self.rows, now=16)
        _, req = self.reply(req, [], "same")
        self.assertEqual(self.reply(req, [], "same"), (True, None))
        self.assertIsNone(self.inventory.catalog)

    def test_bridge_snapshot_is_clean_but_history_and_routing_context_are_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            router = Router(Path(folder) / "config.json", Path(folder))
            router.threads = self.rows
            router.record_history("decision_created", thread="deleted", title="Historic title")
            history = (Path(folder) / "history.jsonl").read_bytes()
            initialize = b'{"id":1,"method":"initialize","params":{"clientInfo":{"name":"test","version":"1"}}}\n'
            self.assertEqual(router.client_line(initialize), initialize)
            self.assertFalse(router.inventory.ready)
            self.assertTrue(router.server_line('{"id":1,"result":{"userAgent":"test"}}'))
            self.assertTrue(router.inventory.ready)
            req = router.inventory.poll(router.threads, now=0)
            self.assertFalse(router.server_line(json.dumps({"id": req["id"], "result": {
                "data": [{"id": "kept", "name": "Current"}], "nextCursor": None}})))
            router.log({"event": "test"})
            snapshot = json.loads((Path(folder) / ("status-%s.json" % os.getpid())).read_text())
            self.assertEqual(set(snapshot["threads"]), {"kept"})
            self.assertEqual(router.threads["kept"]["name"], "Current")
            self.assertIn("deleted", router.threads)
            self.assertEqual((Path(folder) / "history.jsonl").read_bytes(), history)
            self.assertIsNotNone(snapshot["inventory_synced_at"])


if __name__ == "__main__":
    unittest.main()
