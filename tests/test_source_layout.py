"""Exercise relocation, legacy launches and private-data exclusion in fresh processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from codex_model_router.build_identity import identity, router_identity
from tools.packaging.source_tree import stage_source
from tools.packaging import build_linux_package
from tools.packaging.legal import copy_legal_notices, NOTICES


class SourceLayoutTests(unittest.TestCase):
    def test_root_has_only_dispatchers_not_implementation_modules(self):
        self.assertEqual({p.name for p in ROOT.glob('*.py') if p.name != 'build_stamp.py'},
                         {'run.py', 'router.py', 'desktop.py', 'macos.py', 'linux.py',
                          'monitor_service.py', 'monitor_linux.py'})

    def child(self, arguments, cwd):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('PERSONAL_CODEX_ROUTER_') and key not in ('PYTHONPATH', 'PYTHONHOME')}
        return subprocess.run([sys.executable, *map(str, arguments)], cwd=cwd, env=env,
                              capture_output=True, text=True, check=True, timeout=20)

    def test_legacy_launchers_work_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory(prefix='router launch ') as folder:
            for name in ('desktop.py', 'macos.py', 'linux.py', 'monitor_service.py', 'monitor_linux.py'):
                # GTK is optional on Mac/Windows; the source wrapper itself is checked below.
                if name == 'monitor_linux.py':
                    continue
                with self.subTest(launcher=name):
                    output = self.child([ROOT / name, '--help'], folder)
                    self.assertIn('usage:', output.stdout)

    def test_build_snapshot_keeps_structure_and_loaded_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'snapshot'
            stage_source(ROOT, destination)
            self.assertEqual(identity(destination), identity(ROOT))
            self.assertEqual(router_identity(destination), router_identity(ROOT))
            self.assertTrue((destination / 'src/codex_model_router/bridge/router.py').is_file())
            self.assertTrue((destination / 'native/macos/MonitorMac.swift').is_file())
            self.assertTrue((destination / 'native/windows/MonitorWindows.cs').is_file())
            self.assertFalse((destination / 'state').exists())
            self.assertFalse((destination / 'config.local.json').exists())
            self.assertFalse((destination / 'build_stamp.py').exists())
            for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
                self.assertEqual((destination / name).read_bytes(), (ROOT / name).read_bytes())
            output = self.child([destination / 'tools/packaging/runtime_entry.py', 'identity'], folder)
            self.assertEqual(json.loads(output.stdout)['routerBuild'], router_identity(ROOT))

    def test_linux_resources_resolve_without_checkout_or_pythonpath(self):
        with tempfile.TemporaryDirectory(prefix='router resources ') as folder:
            resources = Path(folder) / 'Resources'
            stage_source(ROOT, resources)
            (resources / 'application.json').write_text(json.dumps({'schema': 1, 'layout': 'linux-deb-v1'}))
            code = ('import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); '
                    'runpy.run_module("codex_model_router.packaged_main",run_name="__main__")')
            output = self.child(['-I', '-B', '-c', code, resources / 'src', 'identity'], folder)
            report = json.loads(output.stdout)
            self.assertTrue(report['packaged'])
            self.assertEqual(report['version'], (ROOT / 'VERSION').read_text().strip())
            self.assertFalse((resources / 'config.local.json').exists())

    def test_snapshot_never_copies_private_or_generated_files(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'fixture'
            fixture.mkdir()
            for name in ('run.py', 'build.ps1', 'VERSION', 'config.example.json'):
                (fixture / name).write_text('public')
            for name in ('config.local.json', 'build_stamp.py', 'state/prompts.jsonl',
                         'dist/private.py', 'src/codex_model_router/__pycache__/cached.pyc'):
                path = fixture / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('private sentinel')
            destination = Path(folder) / 'snapshot'
            stage_source(fixture, destination)
            self.assertEqual({str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()},
                             {'run.py', 'build.ps1', 'VERSION', 'config.example.json'})

    def test_package_notices_retain_exact_original_terms(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'legal'
            copy_legal_notices(ROOT, destination)
            self.assertEqual({p.relative_to(destination).as_posix()
                              for p in destination.rglob('*') if p.is_file()}, set(NOTICES))
            for target, source in NOTICES.items():
                self.assertEqual((destination / target).read_bytes(), (ROOT / source).read_bytes())

    def test_missing_or_symlink_notice_aborts_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'source'
            fixture.mkdir()
            destination = Path(folder) / 'payload'
            for relative in NOTICES.values():
                source = fixture / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text('notice')
            missing = fixture / 'monitor-ui/fonts/OFL-Nunito.txt'
            missing.unlink()
            with self.assertRaises(ValueError):
                copy_legal_notices(fixture, destination)
            self.assertFalse(destination.exists())
            external = Path(folder) / 'external.txt'
            external.write_text('private sentinel')
            try:
                missing.symlink_to(external)
            except OSError:
                self.skipTest('Symlink creation is unavailable on this host')
            with self.assertRaises(ValueError):
                copy_legal_notices(fixture, destination)
            self.assertFalse(destination.exists())

    def test_generated_linux_runtime_executes_the_actual_payload(self):
        # Only the host's missing Debian/desktop-validation tools are substituted.
        # Execute the real generated shell launcher against the real staged code.
        real_run = subprocess.run
        observed = []
        with tempfile.TemporaryDirectory(prefix='router deb ') as folder:
            def package_tool(command, **kwargs):
                if command[0] == 'dpkg-deb':
                    application = Path(command[-2]) / 'usr/lib/codex-model-router'
                    resources = application / 'Resources'
                    self.assertTrue((resources / 'src/codex_model_router/bridge/router.py').is_file())
                    self.assertFalse((resources / 'config.local.json').exists())
                    self.assertFalse((resources / 'state').exists())
                    for target, source in NOTICES.items():
                        self.assertEqual((resources / target).read_bytes(), (ROOT / source).read_bytes())
                        self.assertEqual((Path(command[-2]) / 'usr/share/doc/codex-model-router' / target).read_bytes(),
                                         (ROOT / source).read_bytes())
                    env = {key: value for key, value in os.environ.items()
                           if not key.startswith('PERSONAL_CODEX_ROUTER_')
                           and key not in ('PYTHONPATH', 'PYTHONHOME')}
                    result = real_run([str(application / 'bin/router-runtime'), 'identity'],
                                      cwd=folder, env=env, check=True, capture_output=True,
                                      text=True, timeout=20)
                    observed.append(json.loads(result.stdout))
                    Path(command[-1]).write_bytes(b'synthetic Debian container')
                return subprocess.CompletedProcess(command, 0)
            with patch.object(build_linux_package.subprocess, 'run', side_effect=package_tool):
                build_linux_package.build(Path(folder) / 'output')
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0]['packaged'])
        self.assertEqual(observed[0]['version'], (ROOT / 'VERSION').read_text().strip())
