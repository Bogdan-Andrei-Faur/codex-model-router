"""The shared cache now replaces the former Swift-only journal reader."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.monitor.monitor_state import MonitorJournal


class SharedJournalTests(unittest.TestCase):
    def test_append_partial_rotation_truncation_and_no_reread(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.jsonl'
            cache = MonitorJournal()
            path.write_bytes(b''.join(json.dumps({'n': n}).encode()+b'\n' for n in range(35000)))
            self.assertTrue(cache.update(path)); self.assertEqual(len(cache.rows), 35000)
            before = cache.bytes_read
            with patch.object(Path, 'open', side_effect=PermissionError()):
                self.assertFalse(cache.update(path)); self.assertEqual(len(cache.rows), 35000)
            self.assertFalse(cache.update(path)); self.assertEqual(cache.bytes_read, before)
            with path.open('ab') as stream: stream.write(b'{"n":35000')
            self.assertTrue(cache.update(path)); self.assertEqual(len(cache.rows), 35000)
            with path.open('ab') as stream: stream.write(b'}\nnot-json\n{"n":35001}\n')
            self.assertTrue(cache.update(path)); self.assertEqual(len(cache.rows), 35002)
            self.assertLess(cache.bytes_read-before, 100)
            replacement = path.with_suffix('.new'); replacement.write_bytes(b'{"n":8}\n'); replacement.replace(path)
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [{'n': 8}])
            path.write_bytes(b'')
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [])
            path.write_bytes(b'{"n":9}\n')
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [{'n': 9}])
            path.write_bytes(b'{"n":7}\n')
            import os
            stamp=path.stat().st_mtime_ns+5000000000; os.utime(path, ns=(stamp,stamp))
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [{'n': 7}])
            path.unlink()
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [])
            self.assertFalse(cache.update(path))
            path.write_bytes(b'{"n":6}\n')
            self.assertTrue(cache.update(path)); self.assertEqual(cache.rows, [{'n': 6}])


if __name__ == '__main__': unittest.main()
