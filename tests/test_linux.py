import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import codex_model_router.platforms.desktop_runtime as desktop_runtime
import codex_model_router.platforms.linux_desktop as linux_desktop
import codex_model_router.platforms.linux_secret as linux_secret
from codex_model_router.monitor.monitor_state import MonitorState, TELEMETRY_COUNTERS
from codex_model_router.storage.state_store import atomic_json


@unittest.skipUnless(sys.platform == 'linux', 'Linux filesystem and executable semantics')
class LinuxIntegrationTests(unittest.TestCase):
    def test_discovery_uses_desktop_backend_and_rejects_incomplete_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / 'resources').mkdir()
            for name in ('ChatGPT', 'resources/codex'):
                path = app / name
                path.write_text('#!/bin/sh\nexit 0\n')
                path.chmod(0o755)
            found = desktop_runtime.discover_linux(roots=[app])
            self.assertEqual(found.backend, app / 'resources/codex')
            packaged = app / 'resources/codex-cli/bin'
            packaged.mkdir(parents=True)
            with self.assertRaises(desktop_runtime.DiscoveryError):
                desktop_runtime.discover_linux(roots=[app])
            (packaged / 'codex').write_text('#!/bin/sh\nexit 0\n')
            (packaged / 'codex').chmod(0o755)
            self.assertEqual(desktop_runtime.discover_linux(str(app / 'ChatGPT')).backend, packaged / 'codex')

    def environment(self, directory):
        root = Path(directory) / 'router with spaces'
        (root / 'dist').mkdir(parents=True)
        wrapper = root / 'dist/codex-router'
        wrapper.write_text('#!/bin/sh\nprintf "codex-cli test\\n"\n')
        wrapper.chmod(0o755)
        app = Path(directory) / 'data/applications'
        app.mkdir(parents=True)
        return root, app

    def test_install_preserves_original_mcp_launcher_and_uninstall_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root, app = self.environment(directory)
            target = app / 'chatgpt.desktop'
            original = '[Desktop Entry]\nName=ChatGPT\nExec="/custom/mcp launcher" --mode=work %U\nDBusActivatable=true\n\n[Desktop Action new]\nExec=/custom/launcher --new %u\n'
            target.write_text(original)
            target.chmod(0o640)
            found = desktop_runtime.Installation(Path('/test'), Path('/test/codex'), 'test', 'linux-desktop')
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent)}):
                linux_desktop.install(root, {}, found, lambda _: {'handshake': True})
                self.assertTrue(linux_desktop.registered(root))
                modified = target.read_text()
                self.assertIn('"/custom/mcp launcher" --mode=work %U', modified)
                self.assertIn('DBusActivatable=false', modified)
                self.assertEqual(modified.count('codex-desktop'), 2)
                linux_desktop.install(root, {}, found, lambda _: self.fail('Reinstall must be idempotent'))
                linux_desktop.uninstall(root)
                self.assertEqual(target.read_text(), original)
                self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    def test_system_entry_override_is_removed_and_external_changes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root, app = self.environment(directory)
            system = Path(directory) / 'system/applications'
            system.mkdir(parents=True)
            original = '[Desktop Entry]\nExec=/usr/bin/chatgpt %U\n'
            (system / 'chatgpt.desktop').write_text(original)
            found = desktop_runtime.Installation(Path('/test'), Path('/test/codex'), 'test', 'linux-desktop')
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent), 'XDG_DATA_DIRS': str(system.parent)}):
                linux_desktop.install(root, {}, found, lambda _: {})
                installed = (app / 'chatgpt.desktop').read_bytes()
                (app / 'chatgpt.desktop').write_text('external change')
                self.assertFalse(linux_desktop.registered(root))
                with self.assertRaises(desktop_runtime.DiscoveryError):
                    linux_desktop.uninstall(root)
                self.assertEqual((app / 'chatgpt.desktop').read_text(), 'external change')
                (app / 'chatgpt.desktop').write_bytes(installed)
                linux_desktop.uninstall(root)
                self.assertFalse((app / 'chatgpt.desktop').exists())
                self.assertEqual((system / 'chatgpt.desktop').read_text(), original)

    def test_probe_failure_does_not_register_or_modify_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root, app = self.environment(directory)
            target = app / 'chatgpt.desktop'
            target.write_text('[Desktop Entry]\nExec=chatgpt %U\n')
            found = desktop_runtime.Installation(Path('/test'), Path('/test/codex'), 'test', 'linux-desktop')
            def fail(_):
                raise desktop_runtime.DiscoveryError('synthetic probe failure')
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent)}):
                with self.assertRaises(desktop_runtime.DiscoveryError):
                    linux_desktop.install(root, {}, found, fail)
                self.assertEqual(target.read_text(), '[Desktop Entry]\nExec=chatgpt %U\n')
                self.assertIsNone(linux_desktop.registration(root))

    def test_argument_forwarding_without_shell_expansion(self):
        import codex_model_router.platforms.linux as linux
        with patch.object(linux, 'open_monitor'), patch.object(linux.os, 'execvpe') as execute:
            command = ['/custom/mcp launcher', 'a b', '$(touch /tmp/no)', 'https://example.com/?a=1&b=2']
            linux.launch_native(command)
            self.assertEqual(execute.call_args.args[:2], (command[0], command))


class LinuxMonitorContractTests(unittest.TestCase):
    def make(self, directory):
        root = Path(directory)
        atomic_json(root / 'config.local.json', {'enabled': True, 'routes': {}, 'jev': {'connection': 'typesafe', 'api_key': 'PRIVATE_SENTINEL'}})
        return MonitorState(root, ROOT)

    def test_policy_matches_router_migration_without_rewriting_config(self):
        from copy import deepcopy
        from codex_model_router.routing.model_catalog import LEGACY_ROUTES, DEFAULT_ROUTES
        from codex_model_router.bridge.router import read_config
        custom = deepcopy(LEGACY_ROUTES)
        custom['normal']['effort'] = 'high'
        cases = [({'routes': LEGACY_ROUTES}, DEFAULT_ROUTES),
                 ({'routes': custom}, custom),
                 ({'routes': LEGACY_ROUTES, 'model_catalog_version': 'pinned'}, LEGACY_ROUTES)]
        for config, expected in cases:
            with self.subTest(config=config), tempfile.TemporaryDirectory() as directory:
                model = self.make(directory)
                path = model.root / 'config.local.json'
                atomic_json(path, dict(config, jev={'connection': 'vercel', 'api_key': 'PRIVATE_SENTINEL'}))
                original = path.read_bytes()
                payload = model.payload()
                self.assertEqual(payload['config']['routes'], expected)
                self.assertEqual(payload['config']['routes'], read_config(path)['routes'])
                self.assertNotIn('PRIVATE_SENTINEL', json.dumps(payload))
                self.assertEqual(path.read_bytes(), original)

    def test_payload_uses_freshest_row_and_excludes_private_config(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make(directory)
            now = time.time()
            for i in (1, 2):
                atomic_json(model.state / ('status-%d.json' % i), {'pid': os.getpid(), 'heartbeat': now, 'threads': {'task': {'updated': i, 'model': str(i)}}, 'product_version': model.version, 'router_build_id': model.router_build, 'telemetry': {'enabled': True, 'invalid_wire_size': 2}})
            atomic_json(model.state / 'status-stale.json', {'pid': os.getpid(), 'heartbeat': now - 30, 'threads': {'stale': {}}})
            payload = model.payload()
            self.assertEqual(payload['connections'], 2)
            self.assertEqual(payload['threads']['task']['model'], '2')
            self.assertNotIn('stale', payload['threads'])
            self.assertNotIn('PRIVATE_SENTINEL', json.dumps(payload))
            self.assertEqual(payload['telemetry']['invalid_wire_size'], 4)
            self.assertFalse(payload['bridgeBuildMismatch'])

    def test_controls_persist_and_mark_restart_only_when_needed(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make(directory)
            model.configure('enabled', False)
            self.assertFalse(model.payload()['restartRequired'])
            model.configure('phase_routing', True)
            self.assertTrue(model.payload()['restartRequired'])
            self.assertTrue(json.loads((model.state / 'restart-required.json').read_text())['phase_routing'])
            for key, value in [('enabled', 1), ('history_days', True), ('comparison_engines', ['jev', 'jev']), ('codex', '/malicious')]:
                with self.assertRaises(ValueError):
                    model.configure(key, value)
            self.assertFalse(model.payload()['config']['enabled'])
            self.assertEqual((model.root / 'config.local.json').stat().st_mode & 0o777, 0o600) if os.name != 'nt' else None

    def test_history_quality_manual_mode_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make(directory)
            model.state.mkdir(exist_ok=True)
            (model.state / 'history.jsonl').write_text(json.dumps({'decision_id': 'd', 'thread': 't', 'event': 'decision_created'}) + '\n')
            model.quality('d', 'model', 'adequate')
            model.task_mode('t', 'manual')
            self.assertEqual(model.payload()['taskModes']['t'], 'manual')
            self.assertEqual(model.history[-1]['model_quality'], 'adequate')
            with self.assertRaises(ValueError): model.quality('unknown', 'model', 'adequate')
            with self.assertRaises(ValueError): model.task_mode('unknown', 'manual')
            model.preview = True
            with self.assertRaises(ValueError): model.configure('enabled', True)
            with self.assertRaises(ValueError): model.quality('d', 'overall', '')

    def test_all_public_telemetry_counters_are_projected(self):
        from codex_model_router.telemetry.inference_telemetry import LocalInferenceTelemetry
        collector = LocalInferenceTelemetry(lambda _: None)
        try:
            self.assertFalse(set(collector.snapshot()) - {'enabled'} - set(TELEMETRY_COUNTERS))
        finally:
            collector.close()

    def test_secret_values_are_not_arguments_and_cache_is_invalidated(self):
        with tempfile.TemporaryDirectory() as directory:
            model = self.make(directory)
            result = subprocess.CompletedProcess([], 0, 'ok')
            with patch.object(linux_secret.subprocess, 'run', return_value=result) as run:
                self.assertTrue(linux_secret.store_key(model.root, 'jev-typesafe', 'PRIVATE_SENTINEL'))
                self.assertNotIn('PRIVATE_SENTINEL', str(run.call_args.args))
                self.assertEqual(run.call_args.kwargs['input'], 'PRIVATE_SENTINEL')
                self.assertNotIn('PRIVATE_SENTINEL', (model.state / 'keychain-revision.json').read_text())
            with patch.object(linux_secret, 'request', side_effect=['first', 'second']) as request:
                self.assertEqual(linux_secret.read_key(model.state, 'jev-typesafe'), 'first')
                self.assertEqual(linux_secret.read_key(model.state, 'jev-typesafe'), 'first')
                atomic_json(model.state / 'keychain-revision.json', {'jev-typesafe': 'new'})
                self.assertEqual(linux_secret.read_key(model.state, 'jev-typesafe'), 'second')
                self.assertEqual(request.call_count, 2)
            self.assertNotEqual(linux_secret.attributes(model.root, 'jev-typesafe'), linux_secret.attributes(model.root, 'jev-vercel'))


if __name__ == '__main__':
    unittest.main()
