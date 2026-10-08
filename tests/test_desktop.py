import json
import contextlib
import io
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import codex_model_router.platforms.desktop as desktop
import codex_model_router.platforms.desktop_runtime as runtime


class DiscoveryTests(unittest.TestCase):
    def package(self, root, version):
        install = root / version
        resources = install / 'app/resources'
        resources.mkdir(parents=True)
        (install / 'app/ChatGPT.exe').write_bytes(b'desktop')
        for name in ('codex.exe','codex-code-mode-host.exe','codex-windows-sandbox-setup.exe','codex-command-runner.exe','rg.exe'):
            (resources / name).write_bytes((name + version).encode())
        return dict(Name='OpenAI.Codex', Version=version, InstallLocation=str(install), PackageFamilyName='OpenAI.Codex_test')

    def test_update_selects_registered_version_and_keeps_complete_previous_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = self.package(root, '1.9.0.0'); new = self.package(root, '1.10.0.0')
            first = runtime.discover_windows([old],root/'cache')
            second = runtime.discover_windows([old,new],root/'cache')
            self.assertNotEqual(first.backend,second.backend)
            self.assertEqual(second.version,'1.10.0.0')
            self.assertTrue(first.backend.exists())
            self.assertEqual(second.backend.read_bytes(),b'codex.exe1.10.0.0')
            self.assertTrue((second.backend.parent/'codex-code-mode-host.exe').exists())
            self.assertEqual(runtime.discover_windows([new,old],root/'cache').backend,second.backend)

    def test_corrupt_cache_and_incomplete_update_are_detected_without_using_old_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); old=self.package(root,'1.0'); new=self.package(root,'2.0')
            found=runtime.discover_windows([old],root/'cache')
            found.backend.write_bytes(b'broken')
            repaired=runtime.discover_windows([old],root/'cache')
            self.assertNotEqual(repaired.backend,found.backend)
            self.assertEqual(repaired.backend.read_bytes(),b'codex.exe1.0')
            self.assertEqual(found.backend.read_bytes(),b'broken')
            self.assertEqual(runtime.discover_windows([old],root/'cache').backend,repaired.backend)
            (Path(new['InstallLocation'])/'app/resources/codex-command-runner.exe').unlink()
            with self.assertRaisesRegex(runtime.DiscoveryError,'incompleta'):
                runtime.discover_windows([old,new],root/'cache')
            (Path(new['InstallLocation'])/'app/resources/codex.exe').unlink()
            with self.assertRaisesRegex(runtime.DiscoveryError,'incompleta'):
                runtime.discover_windows([old,new],root/'cache')

    def test_no_registered_package_does_not_guess_an_old_hash(self):
        with self.assertRaises(runtime.DiscoveryError): runtime.discover_windows([])

    def test_mac_discovers_bundle_again_after_version_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); app=root/'ChatGPT.app'; contents=app/'Contents'
            (contents/'MacOS').mkdir(parents=True);(contents/'Resources').mkdir()
            for name in ('MacOS/ChatGPT','Resources/codex'):
                (contents/name).write_bytes(b'test');(contents/name).chmod(0o755)
            for version in ('1','2'):
                (contents/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'ChatGPT','CFBundleShortVersionString':version}))
                found=runtime.discover_macos(roots=[root])
                self.assertEqual(found.version,version)
            (contents/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'../../bad'}))
            with self.assertRaises(runtime.DiscoveryError):runtime.discover_macos(roots=[root])

    def test_mac_upgrade_prefers_packaged_launcher_over_legacy_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); app = root / 'ChatGPT.app'; contents = app / 'Contents'
            (contents / 'MacOS').mkdir(parents=True)
            (contents / 'Resources').mkdir()
            (contents / 'Info.plist').write_bytes(plistlib.dumps({
                'CFBundleExecutable': 'ChatGPT', 'CFBundleShortVersionString': '1'}))
            for name in ('MacOS/ChatGPT', 'Resources/codex'):
                (contents / name).write_bytes(b'legacy'); (contents / name).chmod(0o755)
            self.assertEqual(runtime.discover_macos(roots=[root]).backend, contents / 'Resources/codex')
            launcher = contents / 'Resources/codex-cli/bin/codex'
            launcher.parent.mkdir(parents=True)
            launcher.write_bytes(b'packaged'); launcher.chmod(0o755)
            (contents / 'Info.plist').write_bytes(plistlib.dumps({
                'CFBundleExecutable': 'ChatGPT', 'CFBundleShortVersionString': '2'}))
            for explicit in (None, str(app)):
                with self.subTest(explicit=explicit):
                    found = runtime.discover_macos(explicit=explicit, roots=[root])
                    self.assertEqual(found.backend, launcher)
                    self.assertEqual(found.version, '2')
            (contents / 'Resources/codex').unlink()
            self.assertEqual(runtime.discover_macos(roots=[root]).backend, launcher)

    def test_mac_incomplete_packaged_launcher_does_not_use_legacy_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); contents = root / 'ChatGPT.app/Contents'
            (contents / 'MacOS').mkdir(parents=True)
            launcher = contents / 'Resources/codex-cli/bin/codex'
            launcher.parent.mkdir(parents=True)
            (contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': 'ChatGPT'}))
            for name in ('MacOS/ChatGPT', 'Resources/codex'):
                (contents / name).write_bytes(b'legacy'); (contents / name).chmod(0o755)
            with self.assertRaises(runtime.DiscoveryError):
                runtime.discover_macos(roots=[root])
            launcher.write_bytes(b'packaged'); launcher.chmod(0o644)
            # Windows does not implement POSIX executable bits. Model the
            # macOS access check rather than expecting chmod to remove X_OK.
            with patch.object(runtime.os, 'access', side_effect=lambda path, mode: path != launcher):
                with self.assertRaises(runtime.DiscoveryError):
                    runtime.discover_macos(roots=[root])
            launcher.chmod(0o755)
            self.assertEqual(runtime.discover_macos(roots=[root]).backend, launcher)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'dist').mkdir();(self.root/'dist/codex-router.exe').write_bytes(b'wrapper')
        self.cfg={'enabled':True,'routes':{'custom':{}},'history_days':0,
                  'inference_telemetry':True,'prompt_logging':True,'phase_routing':True}
        for key,value in [('ROOT',self.root),('CONFIG',self.root/'config.local.json'),('STATE',self.root/'state')]:
            patcher=patch.object(desktop,key,value);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(desktop.sys,'platform','win32');patcher.start();self.addCleanup(patcher.stop)
        desktop.atomic_json(desktop.CONFIG,self.cfg)
        self.env={'value':None,'kind':1}
        def write(value,kind=1):self.env.update(value=value,kind=kind)
        patches=[patch.object(desktop,'read_environment',side_effect=lambda:dict(self.env)),
                 patch.object(desktop,'probe_bridge',return_value={'handshake':True,'catalog':True}),
                 patch.object(desktop,'write_environment',side_effect=write),
                 patch.object(desktop,'discover',return_value=runtime.Installation(self.root/'ChatGPT.exe',self.root/'codex.exe','2','test')),
                 patch.object(desktop.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'codex-cli 1\n',b''))]
        for patcher in patches:patcher.start();self.addCleanup(patcher.stop)

    def test_registration_is_idempotent_and_uninstall_preserves_data(self):
        self.assertTrue(desktop.install()['registered']);first=desktop.read_registration()
        self.assertTrue(desktop.install()['registered']);self.assertEqual(first['previous'],desktop.read_registration()['previous'])
        self.assertEqual(desktop.config(),dict(self.cfg,installation_mode='auto'))
        (desktop.STATE/'history.jsonl').write_text('history')
        desktop.uninstall()
        self.assertIsNone(self.env['value']);self.assertIsNone(desktop.read_registration())
        self.assertEqual((desktop.STATE/'history.jsonl').read_text(),'history')

    def test_existing_config_gets_active_observability_defaults_without_overwriting_choices(self):
        desktop.atomic_json(desktop.CONFIG, {'enabled': True, 'inference_telemetry': False})
        loaded = desktop.config()
        self.assertFalse(loaded['inference_telemetry'])
        self.assertTrue(loaded['prompt_logging'])
        self.assertTrue(loaded['phase_routing'])
        self.assertEqual(loaded['history_days'], 0)
        self.assertEqual(json.loads(desktop.CONFIG.read_text()), loaded)

    def test_another_integration_is_never_overwritten_or_removed(self):
        self.env['value']='someone-else'
        with self.assertRaises(runtime.DiscoveryError):desktop.install()
        self.assertIsNone(desktop.read_registration());self.assertEqual(desktop.config(),self.cfg)
        self.env['value']=None;desktop.install();self.env['value']='changed-after-install'
        with self.assertRaises(runtime.DiscoveryError):desktop.uninstall()
        self.assertEqual(self.env['value'],'changed-after-install')

    def test_failed_preflight_does_not_register_environment_and_restores_config(self):
        with patch.object(desktop.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'')):
            with self.assertRaises(runtime.DiscoveryError):desktop.install()
        self.assertIsNone(self.env['value']);self.assertEqual(desktop.config(),self.cfg)
        self.assertEqual(desktop.read_registration()['status'],'preparing')

    def test_registration_is_not_live_desktop_evidence_and_smoke_does_not_count(self):
        desktop.install()
        report=desktop.doctor();self.assertEqual(report['connection'],'restart_pending')
        desktop.atomic_json(desktop.STATE/'status-1.json',{'heartbeat':time.time(),'events':[], 'client_name':'other','handshake_complete':True})
        report=desktop.doctor();self.assertEqual(report['connection'],'bridge_observed');self.assertEqual(report['desktop_sessions'],0)
        desktop.atomic_json(desktop.STATE/'status-1.json',{'heartbeat':time.time(),'events':[], 'client_name':'codex_desktop','handshake_complete':True})
        self.assertEqual(desktop.doctor()['connection'],'desktop_connected')
        desktop.atomic_json(desktop.STATE/'status-1.json',{'heartbeat':time.time(),'events':[{'event':'bridge_stopped'}], 'client_name':'codex_desktop','handshake_complete':True})
        self.assertEqual(desktop.doctor()['connection'],'restart_pending')

    def test_login_restore_refuses_missing_wrapper_and_other_connection(self):
        desktop.install();self.env['value']='other'
        self.assertFalse(desktop.restore_session()['restored']);self.assertEqual(self.env['value'],'other')
        self.env['value']=None
        self.assertTrue(desktop.restore_session()['restored'])
        Path(desktop.read_registration()['wrapper']).unlink()
        self.assertFalse(desktop.restore_session()['restored'])

    def test_mac_registration_creates_owned_login_agent_and_removal_preserves_history(self):
        bridge=self.root/'dist/codex-router';bridge.write_text('wrapper');bridge.chmod(0o755)
        desktop.atomic_json(desktop.CONFIG,dict(self.cfg,platform='darwin'))
        agent=self.root/'LaunchAgents/router.plist'
        with patch.object(desktop.sys,'platform','darwin'),patch.object(desktop,'agent_path',return_value=agent),patch.object(os,'getuid',return_value=501,create=True):
            desktop.install()
            data=plistlib.loads(agent.read_bytes())
            self.assertEqual(data['ProgramArguments'],[sys.executable,str(self.root/'desktop.py'),'restore-session'])
            self.assertTrue(data['RunAtLoad']);self.assertNotIn('KeepAlive',data)
            desktop.uninstall();self.assertFalse(agent.exists());self.assertIsNone(self.env['value'])

    def test_mac_never_activates_copied_windows_configuration(self):
        with patch.object(desktop.sys,'platform','darwin'):
            with self.assertRaisesRegex(runtime.DiscoveryError,'otra instalación'):desktop.install()
        self.assertIsNone(self.env['value'])

    def test_protocol_failure_keeps_desktop_unregistered(self):
        with patch.object(desktop,'probe_bridge',side_effect=runtime.DiscoveryError('incompatible')):
            with self.assertRaises(runtime.DiscoveryError):desktop.install()
        self.assertIsNone(self.env['value']);self.assertEqual(desktop.config(),self.cfg)

    def test_cli_connection_failure_returns_actionable_code(self):
        output=io.StringIO();error=io.StringIO()
        with patch.object(sys,'argv',['desktop','install']), \
             patch.object(desktop,'install',side_effect=runtime.DiscoveryError('Safe failure',code='source_bridge_active')), \
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):
            self.assertEqual(desktop.main(),1)
        self.assertEqual(output.getvalue(),'')
        self.assertEqual(json.loads(error.getvalue()),{'error':'Safe failure','code':'source_bridge_active'})
        self.assertIsNone(self.env['value']);self.assertIsNone(desktop.read_registration())

    def test_localized_cli_error_is_valid_utf8_json_through_windows_ansi_pipe(self):
        raw=io.BytesIO();error=io.TextIOWrapper(raw,encoding='cp1252')
        with patch.object(sys,'argv',['desktop','install']), \
             patch.object(desktop,'install',side_effect=runtime.DiscoveryError('No se pudo verificar la conexión anterior.',code='source_connection_unverified')), \
             contextlib.redirect_stderr(error):
            self.assertEqual(desktop.main(),1)
        error.flush()
        encoded=raw.getvalue()
        self.assertTrue(encoded.isascii())
        self.assertEqual(json.loads(encoded)['error'],'No se pudo verificar la conexión anterior.')
        self.assertEqual(json.loads(encoded)['code'],'source_connection_unverified')
        error.detach()

    def imported_setup(self):
        legacy=self.root/'legacy';(legacy/'dist').mkdir(parents=True);(legacy/'state').mkdir()
        wrapper=legacy/'dist/codex-router.exe';wrapper.touch()
        desktop.atomic_json(legacy/'state/desktop-integration.json',{'schema':1,'status':'registered','platform':'win32',
                            'wrapper':str(wrapper.resolve()),'previous':{'value':None,'kind':1}})
        desktop.atomic_json(desktop.STATE/'legacy-installation.json',{'schema':1,'root':str(legacy)})
        self.env['value']=str(wrapper.resolve())
        return wrapper

    def test_imported_connection_transfer_and_disconnect_preserve_original_environment(self):
        legacy=self.imported_setup();original=desktop.ROOT/'legacy/state/desktop-integration.json';before=original.read_bytes()
        with patch.object(desktop,'manifest',return_value={'layout':'windows-install-v1'}),patch.object(desktop,'wrapper_path',return_value=self.root/'dist/codex-router.exe'):
            self.assertTrue(desktop.install()['registered'])
        self.assertEqual(desktop.read_registration()['previous'],{'value':None,'kind':1})
        self.assertEqual(original.read_bytes(),before)
        desktop.uninstall();self.assertIsNone(self.env['value'])

    def test_active_imported_source_registration_only_selects_next_launch(self):
        self.imported_setup();snapshot=desktop.ROOT/'legacy/state/status-fixture.json'
        snapshot.write_text(json.dumps({'pid':os.getpid(),'heartbeat':time.time(),'events':[]}));before=snapshot.read_bytes()
        with patch.object(desktop,'manifest',return_value={'layout':'windows-install-v1'}), \
             patch.object(desktop,'wrapper_path',return_value=self.root/'dist/codex-router.exe'), \
             patch('codex_model_router.platforms.installation_migration.reject_active',side_effect=AssertionError('Do not import live data')):
            self.assertTrue(desktop.install()['registered'])
        self.assertEqual(self.env['value'],str((self.root/'dist/codex-router.exe').resolve()))
        self.assertEqual(snapshot.read_bytes(),before)

    def test_failed_transfer_can_be_retried_without_partial_registration(self):
        legacy=self.imported_setup()
        with patch.object(desktop,'manifest',return_value={'layout':'windows-install-v1'}),patch.object(desktop,'wrapper_path',return_value=self.root/'dist/codex-router.exe'):
            with patch.object(desktop,'probe_bridge',side_effect=runtime.DiscoveryError('fixture failure')):
                with self.assertRaises(runtime.DiscoveryError):desktop.install()
            self.assertIsNone(desktop.read_registration());self.assertEqual(self.env['value'],str(legacy.resolve()))
            self.assertTrue(desktop.install()['registered'])

    def test_environment_changed_during_transfer_is_preserved(self):
        legacy=self.imported_setup()
        def concurrent_change(*args):
            self.env['value']='foreign-changed-during-probe';return {'handshake':True}
        with patch.object(desktop,'manifest',return_value={'layout':'windows-install-v1'}),patch.object(desktop,'wrapper_path',return_value=self.root/'dist/codex-router.exe'),patch.object(desktop,'probe_bridge',side_effect=concurrent_change):
            with self.assertRaises(runtime.DiscoveryError):desktop.install()
        self.assertEqual(self.env['value'],'foreign-changed-during-probe');self.assertIsNone(desktop.read_registration())


if __name__=='__main__': unittest.main()
