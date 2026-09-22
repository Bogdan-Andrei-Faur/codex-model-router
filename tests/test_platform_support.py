import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import macos
import decision_engines
from platform_support import backend_path, uses_stdio

ROOT = Path(__file__).resolve().parents[1]


class PlatformTests(unittest.TestCase):
    def test_keychain_lookup_keeps_secret_out_of_command_and_uses_exact_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / 'state'
            state.mkdir()
            decision_engines._KEYCHAIN_CACHE.clear()
            result = subprocess.CompletedProcess([], 0, b'synthetic-test-key\n', b'')
            with patch.object(decision_engines.sys, 'platform', 'darwin'), patch.object(decision_engines.subprocess, 'run', return_value=result) as run:
                self.assertEqual(decision_engines._keychain_key(state,'jev'), 'synthetic-test-key')
                self.assertEqual(decision_engines._keychain_key(state,'jev'), 'synthetic-test-key')
                self.assertEqual(run.call_count, 1)
                args = run.call_args.args[0]
                self.assertNotIn('synthetic-test-key', args)
                self.assertEqual(args[-3:], ['-a','jev','-w'])
                self.assertTrue(args[3].startswith('local.codex-model-router.'))
                self.assertEqual(run.call_args.kwargs['timeout'], 45)
                self.assertIsNone(decision_engines._keychain_key(state,'unknown'))
            (state / 'keychain-revision.json').write_text(json.dumps({'jev':'new'}), encoding='utf-8')
            updated = subprocess.CompletedProcess([], 0, b'updated-test-key\n', b'')
            with patch.object(decision_engines.sys, 'platform', 'darwin'), patch.object(decision_engines.subprocess, 'run', return_value=updated) as run:
                self.assertEqual(decision_engines._keychain_key(state,'jev'), 'updated-test-key')
                self.assertEqual(run.call_count, 1)
            decision_engines._KEYCHAIN_CACHE.clear()
            with patch.object(decision_engines.sys, 'platform', 'darwin'), patch.object(decision_engines.subprocess, 'run', side_effect=subprocess.TimeoutExpired('security',45)):
                self.assertIsNone(decision_engines._keychain_key(state,'jev'))

    def test_real_desktop_global_config_invocation(self):
        self.assertTrue(uses_stdio(["-c", "model=\"gpt-6-astra\"", "app-server", "--analytics-default-enabled", "-c", "model_reasoning_effort=\"high\""]))
        self.assertTrue(uses_stdio(["--config=x=1", "--enable", "feature", "app-server"]))
        self.assertFalse(uses_stdio(["-c", "x=1", "exec", "app-server"]))
        self.assertFalse(uses_stdio(["-c", "app-server"]))
        self.assertFalse(uses_stdio(["app-server", "--listen=stdio://", "--listen=ws://localhost:1"]))

    def test_only_stdio_server_is_intercepted(self):
        for args in (["app-server"], ["app-server", "--listen", "stdio://"], ["app-server", "--listen=stdio://"]):
            self.assertTrue(uses_stdio(args), args)
        for args in (["--version"], ["exec", "app-server"], ["app-server", "generate-json-schema"],
                     ["app-server", "--listen", "ws://127.0.0.1:1234"],
                     ["app-server", "--listen=unix:///tmp/test"], ["app-server", "--listen"],
                     ["app-server", "--listen=tcp://localhost:1234"]):
            self.assertFalse(uses_stdio(args), args)

    @unittest.skipIf(os.name == "nt", "POSIX executable and argv semantics")
    def test_discovery_and_wrapper_support_spaces_unicode_and_quotes(self):
        with tempfile.TemporaryDirectory(prefix="router ' español ") as folder:
            root = Path(folder)
            app = root / "ChatGPT.app"
            (app / "Contents/MacOS").mkdir(parents=True)
            (app / "Contents/Resources").mkdir()
            with (app / "Contents/Info.plist").open("wb") as stream:
                plistlib.dump({"CFBundleExecutable": "ChatGPT"}, stream)
            for file in [app / "Contents/MacOS/ChatGPT", app / "Contents/Resources/codex"]:
                file.write_text("#!/bin/sh\nexit 0\n"); file.chmod(0o755)
            found, desktop, binary = macos.discover_app(str(app))
            self.assertEqual(found, app.resolve())
            self.assertEqual(backend_path({"codex": str(binary)}), binary)
            script = root / "echo args.py"
            script.write_text("import json, sys; print(json.dumps(sys.argv[1:]))")
            wrapper = root / "launcher"
            macos.wrapper(wrapper, [sys.executable, script])
            args = ["", "a b", "a'b", 'a"b', "$(do-not-execute)", "á\\"]
            result = subprocess.run([str(wrapper), *args], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), args)
            binary.chmod(0o644)
            with self.assertRaises(ValueError): backend_path({"codex": str(binary)})

    def test_atomic_pause_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(macos, "ROOT", root), patch.object(macos, "CONFIG", root / "config.local.json"):
                original = {"routes": {"custom": "unchanged"}, "enabled": True}
                macos.save_config(original)
                original["enabled"] = False
                macos.save_config(original)
                self.assertEqual(json.loads(macos.CONFIG.read_text()), original)
                if os.name != "nt": self.assertEqual(macos.CONFIG.stat().st_mode & 0o777, 0o600)

    def test_running_desktop_refuses_launch(self):
        with patch.object(macos.CONFIG.__class__, "read_text", return_value=json.dumps({"desktop": "/test/ChatGPT", "codex": "/test/codex"})), \
             patch.object(macos, "backend_path"), patch.object(macos, "app_running", return_value=True), \
             patch.object(macos.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "sigue abierto"): macos.open_app()
            spawn.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX termination and signal behavior")
    def test_bridge_preserves_protocol_and_stops_child_on_sigterm(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backend = root / "codex"
            pidfile = root / "backend.pid"
            backend.write_text("#!" + sys.executable + "\nimport os,sys\n"
                               "from pathlib import Path\nPath(" + repr(str(pidfile)) + ").write_text(str(os.getpid()))\n"
                               "for line in sys.stdin.buffer:\n sys.stdout.buffer.write(line); sys.stdout.buffer.flush()\n")
            backend.chmod(0o755)
            config = root / "config.json"
            config.write_text(json.dumps({"codex": str(backend), "enabled": False}))
            env = dict(os.environ, PERSONAL_CODEX_ROUTER_CONFIG=str(config),
                       PERSONAL_CODEX_ROUTER_STATE=str(root / "state"))
            proc = subprocess.Popen([sys.executable, str(ROOT / "router.py"), "app-server"], env=env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                payload = b'{"method":"unknown/future","params":{"text":"hola"}}\n'
                proc.stdin.write(payload); proc.stdin.flush()
                # communicate timeout also protects against a bridge startup failure.
                import select
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), payload)
                pid = int(pidfile.read_text())
                proc.terminate()
                proc.wait(timeout=8)
                self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
                with self.assertRaises(ProcessLookupError): os.kill(pid, 0)
            finally:
                if proc.poll() is None: proc.kill(); proc.wait(timeout=5)
                for stream in (proc.stdin, proc.stdout, proc.stderr): stream.close()


if __name__ == "__main__":
    unittest.main()
