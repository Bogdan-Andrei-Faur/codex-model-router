"""Track native command sessions without retaining commands or tool output."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OwnedProcess:
    thread: str
    process_id: str


class CommandProcesses:
    """Associate trusted native process IDs with their exact thread and turn."""

    def __init__(self):
        self.running = {}
        self.interrupted = set()

    @staticmethod
    def _process_id(value):
        return value if isinstance(value, str) and value else None

    def register(self, thread, turn, item, process_id):
        process_id = self._process_id(process_id)
        if not all(isinstance(value, str) and value for value in (thread, turn, item)) or process_id is None:
            return []
        key = (thread, turn, item)
        owned = OwnedProcess(thread, process_id)
        self.running[key] = owned
        return [owned] if (thread, turn) in self.interrupted else []

    def interrupt(self, thread, turn):
        if not isinstance(thread, str) or not thread or not isinstance(turn, str) or not turn:
            return []
        self.interrupted.add((thread, turn))
        matches = [owned for (tid, turn_id, _), owned in self.running.items()
                   if tid == thread and turn_id == turn]
        for key in [key for key in self.running if key[:2] == (thread, turn)]:
            self.running.pop(key, None)
        return matches

    def finish_item(self, thread, turn, item):
        self.running.pop((thread, turn, item), None)

    def finish_turn(self, thread, turn):
        for key in [key for key in self.running if key[:2] == (thread, turn)]:
            self.running.pop(key, None)
        self.interrupted.discard((thread, turn))
