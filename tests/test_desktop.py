import json
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
import desktop
import desktop_runtime as runtime


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


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'dist').mkdir();(self.root/'dist/codex-router.exe').write_bytes(b'wrapper')
        self.cfg={'enabled':True,'routes':{'custom':{}},'provider':{'id':'ollama'},'history_days':0}
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


if __name__=='__main__': unittest.main()
