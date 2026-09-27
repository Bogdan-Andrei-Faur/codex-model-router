from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_control import CommandProcesses, OwnedProcess


class CommandProcessTests(unittest.TestCase):
    def test_interrupt_returns_only_exact_thread_and_turn(self):
        registry = CommandProcesses()
        registry.register("thread-a", "turn-a", "item-a", "process-a")
        registry.register("thread-b", "turn-b", "item-b", "process-b")
        self.assertEqual(registry.interrupt("thread-a", "turn-a"),
                         [OwnedProcess("thread-a", "process-a")])
        self.assertEqual(registry.running, {("thread-b", "turn-b", "item-b"):
                                            OwnedProcess("thread-b", "process-b")})

    def test_late_start_after_interrupt_is_immediately_returned(self):
        registry = CommandProcesses()
        self.assertEqual(registry.interrupt("thread", "turn"), [])
        self.assertEqual(registry.register("thread", "turn", "item", "process"),
                         [OwnedProcess("thread", "process")])

    def test_invalid_or_completed_process_is_not_returned(self):
        registry = CommandProcesses()
        self.assertEqual(registry.register("thread", "turn", "item", 1), [])
        registry.register("thread", "turn", "item", "process")
        registry.finish_item("thread", "turn", "item")
        self.assertEqual(registry.interrupt("thread", "turn"), [])


if __name__ == "__main__":
    unittest.main()
