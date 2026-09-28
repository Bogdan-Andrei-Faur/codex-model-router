import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from control_contract import approval_command, exact_approval_command
from control_runtime import process_alive, process_state, sleep_command, read_process_marker, host_probe_pids


class ControlPortabilityTests(unittest.TestCase):
    def test_exact_powershell_marker_with_spaces_and_quotes(self):
        marker = r"C:\Users\Test User\probe's folder\marker"
        command = approval_command(marker, windows=True)
        self.assertIn("probe''s folder", command)
        self.assertTrue(exact_approval_command(command, marker, windows=True))
        wrapped = subprocess.list2cmdline(['powershell.exe', '-NoProfile', '-Command', command])
        self.assertTrue(exact_approval_command(wrapped, marker, windows=True))
        self.assertTrue(exact_approval_command(wrapped.replace('\\', '\\\\'), marker, windows=True))
        for bad in (command + '; exit', wrapped + ' extra', command.replace('APPROVED', 'OTHER'),
                    subprocess.list2cmdline([r'C:\untrusted\powershell.exe', '-Command', command])):
            self.assertFalse(exact_approval_command(bad, marker, windows=True))

    def test_posix_marker_with_spaces_and_quotes(self):
        marker = "/tmp/probe's folder/marker"
        self.assertTrue(exact_approval_command(approval_command(marker, windows=False), marker, windows=False))

    def test_liveness_check_does_not_signal_process(self):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'], creationflags=flags) as child:
            try:
                self.assertTrue(process_alive(child.pid))
                self.assertTrue(process_alive(child.pid))
                self.assertIsNone(child.poll())
            finally:
                child.terminate()
                child.wait(timeout=5)
            self.assertFalse(process_alive(child.pid))
            self.assertEqual(process_state(child.pid), '')

    def test_sleep_fixture_is_portable_python(self):
        with tempfile.TemporaryDirectory(prefix='probe with spaces ') as folder:
            marker = Path(folder) / 'running.json'
            command = sleep_command(marker)
            source = marker.with_suffix('.py').read_text()
            compile(source, 'fixture', 'exec')
            self.assertIn('sys.executable', source)
            self.assertNotIn("['sleep'", source)
            self.assertIn(str(marker.with_suffix('.py')), command)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux PID namespaces')
    def test_namespaced_probe_ids_are_matched_to_exact_script_and_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'probe/running.json'
            for pid, parent, inner, args in [(2, 0, 2, b'kthreadd'), (90, 80, 2, str(marker.with_suffix('.py')).encode()), (91, 90, 3, b'python'), (99, 1, 3, b'other')]:
                d = root / str(pid)
                d.mkdir()
                (d / 'status').write_text('PPid: %s\nNSpid: %s %s\n' % (parent, pid, inner))
                (d / 'cmdline').write_bytes(b'python\0' + args + b'\0')
            self.assertEqual(host_probe_pids(marker, [2, 3], root), [90, 91])
            (root / '90/cmdline').write_bytes(b'unrelated')
            with self.assertRaises(RuntimeError):
                host_probe_pids(marker, [2, 3], root)

    def test_marker_waits_for_windows_writer_and_complete_json(self):
        with patch.object(Path, 'read_text', side_effect=[PermissionError(), '[', '[42,43]']):
            self.assertEqual(read_process_marker('synthetic.json'), [42, 43])


if __name__ == '__main__':
    unittest.main()
