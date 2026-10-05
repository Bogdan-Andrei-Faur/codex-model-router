"""Package migration and launcher lifetime, without host configuration changes."""
import json
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shlex
import unittest
from unittest.mock import patch

from application_layout import credential_namespace, installed_path
from desktop_runtime import DiscoveryError, Installation
from linux_onboarding import import_installation, error_detail
from installation_migration import MigrationError
import linux_legacy_handoff as handoff
import linux_desktop as integration
from state_store import atomic_json


@unittest.skipUnless(sys.platform == 'linux', 'Linux launchers and permissions')
class LinuxPackageTests(unittest.TestCase):
    def test_onboarding_explains_known_failures_without_leaking_unknown_exception(self):
        error=MigrationError('active_bridge','Codex sigue abierto.')
        self.assertEqual(error_detail(error),'Codex sigue abierto.')
        self.assertNotIn('PRIVATE_SENTINEL',error_detail(ValueError('PRIVATE_SENTINEL')))

    def handoff_fixture(self, base):
        legacy=base/'legacy checkout';root=base/'new data'
        (legacy/'dist').mkdir(parents=True)
        atomic_json(legacy/'config.local.json',{'platform':'linux','python':sys.executable})
        originals={
            'codex-router':'#!/bin/sh\nexport PERSONAL_CODEX_ROUTER_CONFIG='+shlex.quote(str(legacy/'config.local.json'))+'\nexport PYTHONUTF8=1\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(legacy/'router.py'))+' "$@"\n',
            'codex-monitor-linux':'#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(legacy/'monitor_linux.py'))+' "$@"\n',
            'codex-desktop':'#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(legacy/'linux.py'))+' launch-native -- "$@"\n'}
        for name,text in originals.items():
            path=legacy/'dist'/name;path.write_text(text);path.chmod(0o755)
        package=base/'package';package.mkdir()
        for name in ('bridge','monitor','native','codex-desktop'):
            path=package/name
            path.write_text('#!'+sys.executable+'\nimport json,os,sys\nprint(json.dumps({"args":sys.argv[1:],"root":os.environ.get("PERSONAL_CODEX_ROUTER_ROOT"),"legacy_config":os.environ.get("PERSONAL_CODEX_ROUTER_CONFIG")}))\n')
            path.chmod(0o755)
        return legacy,root,package,originals

    def test_cached_desktop_launchers_use_new_root_and_survive_package_removal(self):
        with tempfile.TemporaryDirectory(prefix='router migration ') as folder:
            legacy,root,package,originals=self.handoff_fixture(Path(folder))
            for _ in range(2):
                result=handoff.redirect_launchers(root,legacy,package/'bridge',package/'monitor',package/'native')
                self.assertTrue(result['redirected'])
            receipt=json.loads((root/'state/legacy-launchers.json').read_text())
            for name,original in originals.items():
                self.assertEqual(base64.b64decode(receipt['entries'][name]['original']).decode(),original)
            env=dict(os.environ,PERSONAL_CODEX_ROUTER_CONFIG='/old/config.local.json',PERSONAL_CODEX_ROUTER_ROOT='/old/root')
            args=['a b','$(exit 99)','https://example.com/?a=1&b=2']
            for name in originals:
                reply=json.loads(subprocess.check_output([str(legacy/'dist'/name),*args],env=env,text=True))
                self.assertEqual(reply['root'],str(root));self.assertEqual(reply['args'],args)
                self.assertIsNone(reply['legacy_config'])
            (package/'bridge').unlink();(package/'monitor').unlink()
            (package/'codex-desktop').unlink()
            reply=json.loads(subprocess.check_output([str(legacy/'dist/codex-router'),*args],env=env,text=True))
            self.assertEqual(reply['args'],args);self.assertIsNone(reply['root'])
            self.assertEqual(subprocess.check_output([str(legacy/'dist/codex-monitor-linux')],text=True),'')
            original=[str(package/'native'),*args]
            reply=json.loads(subprocess.check_output([str(legacy/'dist/codex-desktop'),*original],env=env,text=True))
            self.assertEqual(reply['args'],args);self.assertIsNone(reply['root'])

    def test_handoff_preserves_custom_launchers_and_rolls_back_partial_write(self):
        for customized in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                legacy,root,package,_=self.handoff_fixture(Path(folder))
                if customized:(legacy/'dist/codex-router').write_text('custom launcher')
                before={p:p.read_bytes() for p in (legacy/'dist').iterdir()}
                original_write=handoff.atomic_text
                def fail_monitor(path,text,mode):
                    if Path(path).name=='codex-monitor-linux':raise OSError('synthetic write failure')
                    return original_write(path,text,mode)
                context=patch.object(handoff,'atomic_text',side_effect=fail_monitor) if not customized else patch.object(handoff,'atomic_text',wraps=original_write)
                with context:
                    with self.assertRaises((DiscoveryError,OSError)):
                        handoff.redirect_launchers(root,legacy,package/'bridge',package/'monitor',package/'native')
                for path,body in before.items():self.assertEqual(path.read_bytes(),body)


    def fixture(self, base):
        legacy = base / 'old checkout'
        legacy.mkdir()
        atomic_json(legacy / 'config.local.json', {'platform': 'linux', 'enabled': False})
        (legacy / 'dist').mkdir()
        wrapper = legacy / 'dist/codex-router'
        wrapper.write_text('#!/bin/sh\nprintf "codex-cli fixture\\n"\n')
        wrapper.chmod(0o755)
        app = base / 'xdg/applications'
        app.mkdir(parents=True)
        original = '[Desktop Entry]\nExec=/original/desktop %U\n'
        (app / 'chatgpt.desktop').write_text(original)
        found = Installation(Path('/fixture'), Path('/fixture/codex'), 'fixture', 'linux-desktop')
        return legacy, app, original, found

    def test_import_and_connection_transfer_restore_true_original(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            legacy, app, original, found = self.fixture(base)
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent)}):
                integration.install(legacy, {}, found, lambda _: {})
                old_shortcut = (app / 'chatgpt.desktop').read_bytes()
                target = base / 'user data'
                import_installation(legacy, target)
                self.assertEqual(credential_namespace(target), credential_namespace(legacy))
                self.assertEqual((app / 'chatgpt.desktop').read_bytes(), old_shortcut)
                self.assertFalse((target / 'state/desktop-integration.json').exists())
                package_launcher = base / 'package/bin/codex-desktop'
                package_launcher.parent.mkdir(parents=True)
                package_launcher.write_text('#!/bin/sh\nexit 0\n'); package_launcher.chmod(0o755)
                integration.install(target, {}, found, lambda _: {},
                                    wrapper=legacy / 'dist/codex-router', launcher=package_launcher)
                self.assertTrue(integration.registered(target))
                self.assertFalse(integration.registered(legacy))
                with self.assertRaises(DiscoveryError):
                    integration.uninstall(legacy)
                integration.uninstall(target)
                self.assertEqual((app / 'chatgpt.desktop').read_text(), original)
                self.assertTrue((legacy / 'config.local.json').exists())
                integration.install(target, {}, found, lambda _: {},
                                    wrapper=legacy / 'dist/codex-router', launcher=package_launcher)
                self.assertTrue(integration.registered(target))

    def test_transfer_rejects_active_source_and_external_shortcut_changes(self):
        for active in (True, False):
            with tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                legacy, app, _, found = self.fixture(base)
                with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent)}):
                    integration.install(legacy, {}, found, lambda _: {})
                    target = base / 'data'
                    import_installation(legacy, target)
                    if active:
                        atomic_json(legacy / 'state/status-test.json', {'pid': os.getpid()})
                    else:
                        (app / 'chatgpt.desktop').write_text('[Desktop Entry]\nExec=/external\n')
                    before = (app / 'chatgpt.desktop').read_bytes()
                    with self.assertRaises((DiscoveryError, ValueError)):
                        integration.install(target, {}, found, lambda _: {},
                            wrapper=legacy / 'dist/codex-router', launcher=base / 'launcher')
                    self.assertEqual((app / 'chatgpt.desktop').read_bytes(), before)
                    self.assertFalse((target / 'state/desktop-integration.json').exists())

    def test_transfer_write_failure_restores_previous_router_shortcut(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            legacy, app, _, found = self.fixture(base)
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(app.parent)}):
                integration.install(legacy, {}, found, lambda _: {})
                target = base / 'data'; import_installation(legacy, target)
                before = (app / 'chatgpt.desktop').read_bytes()
                def fail_commit(path, value):
                    if value.get('status') == 'registered':
                        raise OSError('synthetic write failure')
                    atomic_json(path, value)
                with patch.object(integration, 'atomic_json', side_effect=fail_commit):
                    with self.assertRaises(OSError):
                        integration.install(target, {}, found, lambda _: {},
                            wrapper=legacy / 'dist/codex-router', launcher=base / 'launcher')
                self.assertEqual((app / 'chatgpt.desktop').read_bytes(), before)
                self.assertTrue(integration.registered(legacy))

    def test_removed_package_falls_back_to_original_argv_without_shell_expansion(self):
        with tempfile.TemporaryDirectory(prefix='router package ') as folder:
            base = Path(folder)
            package = base / 'package launcher'
            package.write_text('#!/bin/sh\nprintf "packaged\\n"\n'); package.chmod(0o755)
            launcher = integration.fallback_launcher(base / 'data', package)
            payload = ['a b', '$(exit 99)', '`exit 99`', 'https://example.com/?x=1&y=2']
            command = [str(launcher), sys.executable, '-c', 'import json,sys; print(json.dumps(sys.argv[1:]))', *payload]
            self.assertEqual(subprocess.check_output(command, text=True).strip(), 'packaged')
            package.unlink()
            self.assertEqual(json.loads(subprocess.check_output(command, text=True)), payload)

    def test_linux_manifest_relocation_and_escape_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            resources = base / 'relocated/Resources'; resources.mkdir(parents=True)
            runtime = resources.parent / 'bin/runtime'; runtime.parent.mkdir(); runtime.touch()
            manifest = {'schema': 1, 'layout': 'linux-deb-v1', 'runtime': 'bin/runtime'}
            atomic_json(resources / 'application.json', manifest)
            self.assertEqual(installed_path(resources, 'runtime'), runtime)
            atomic_json(resources / 'application.json', dict(manifest, runtime='../outside'))
            with self.assertRaises(ValueError):
                installed_path(resources, 'runtime')


if __name__ == '__main__':
    unittest.main()
