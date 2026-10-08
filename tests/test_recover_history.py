import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.storage.recover_history import recover, recover_records


class RecoveryTests(unittest.TestCase):
    def snapshot(self):
        accepted = {"event": "turn_accepted", "thread": "task", "time": "2026-09-21T10:00:00Z",
                    "model": "gpt-5.6-sol", "effort": "high", "reason": "complex work"}
        return {"pid": 42, "threads": {"task": {"name": "Task", "tokens": {"inputTokens": 999}}},
                "events": [accepted, {"event": "turn_completed", "thread": "task"}, dict(accepted)]}

    def test_same_task_same_second_keeps_distinct_executions(self):
        records = recover_records(self.snapshot())
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["decision_id"], records[1]["decision_id"])
        self.assertEqual([r["status"] for r in records], ["finished", "unknown"])
        self.assertTrue(all("inputTokens" not in r for r in records))
        self.assertTrue(all("no conservó" in r["effort_reason"] for r in records))

    def test_rerun_preserves_destination_and_never_touches_source(self):
        with tempfile.TemporaryDirectory() as root:
            source, destination = Path(root) / "status.json", Path(root) / "history.recovered.jsonl"
            source.write_text(json.dumps(self.snapshot()), encoding="utf-8")
            before = source.read_bytes()
            self.assertEqual(recover(source, destination), 2)
            first = destination.read_bytes()
            self.assertEqual(recover(source, destination), 0)
            self.assertEqual(destination.read_bytes(), first)
            self.assertEqual(source.read_bytes(), before)

    def test_modern_decisions_are_not_reimported(self):
        data = self.snapshot()
        for event in data["events"]:
            if event["event"] == "turn_accepted":
                event["decision_id"] = "modern-id"
        self.assertEqual(recover_records(data), [])


if __name__ == "__main__":
    unittest.main()
