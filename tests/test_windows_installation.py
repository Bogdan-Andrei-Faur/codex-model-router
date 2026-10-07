"""Installed Windows ownership and import contracts; no real registration."""
import json
import os
import hashlib
import ctypes
import contextlib
import io
import sys
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import application_layout as layout
from desktop_runtime import DiscoveryError
from windows_connection import imported_connection
from installation_migration import reject_active, import_legacy, MigrationError, snapshot_pid_reused, windows_process_started_at


class WindowsInstallationTests(unittest.TestCase):
    def test_original_windows_config_import_is_normalized_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'legacy';source.mkdir()
            original=b'{"enabled":false,"history_days":90,"routing_engine":"jev"}'
            (source/'config.local.json').write_bytes(original)
            destination=Path(folder)/'new'
            import_legacy(source,destination,platform='win32')
            self.assertEqual((source/'config.local.json').read_bytes(),original)
            expected=dict(json.loads(original),platform='win32')
            self.assertEqual(json.loads((destination/'config.local.json').read_bytes()),expected)
            self.assertFalse(layout.bootstrap(source,destination,platform='win32'))

    def test_missing_platform_is_only_accepted_for_legacy_windows(self):
        for declared,target in ((None,'linux'),(None,'darwin'),('linux','win32'),('darwin','win32'),('', 'win32')):
            with tempfile.TemporaryDirectory() as folder:
                source=Path(folder)/'legacy';source.mkdir()
                value={} if declared is None else {'platform':declared}
                (source/'config.local.json').write_text(json.dumps(value))
                destination=Path(folder)/'new'
                with self.assertRaises(MigrationError) as error:
                    import_legacy(source,destination,platform=target)
                self.assertEqual(error.exception.code,'foreign_platform')
                self.assertFalse(destination.exists())

    def test_packaged_import_returns_safe_reason_instead_of_swallowing_failure(self):
        import packaged_main
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ):
            destination=Path(folder)/'new'
            argv=['packaged_main','--data-root',str(destination),'import-legacy',str(Path(folder)/'missing')]
            for code in ('busy_source','active_bridge','foreign_platform','occupied_destination','missing_config'):
                output=io.StringIO()
                with patch.object(sys,'argv',argv), patch.object(sys,'platform','win32'), \
                     patch('installation_migration.import_legacy',side_effect=MigrationError(code,'PRIVATE_VALUE')), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(packaged_main.main(),1)
                self.assertEqual(json.loads(output.getvalue()),{'error':{'code':code}})
                self.assertNotIn('PRIVATE_VALUE',output.getvalue())
                self.assertFalse(destination.exists())

    def test_stable_bridge_and_runtime_have_distinct_owned_bases(self):
        with tempfile.TemporaryDirectory() as folder:
            app=Path(folder)/'Application';resources=app/'versions/0.8.1-aaaaaaaaaaaaaaaa/Resources';resources.mkdir(parents=True)
            runtime=resources.parent/'runtime/runtime.exe';runtime.parent.mkdir();runtime.touch()
            bridge=app/'bin/codex-router.exe';bridge.parent.mkdir();bridge.touch()
            manifest={'schema':1,'layout':'windows-install-v1','runtime':'runtime/runtime.exe','bridge':'bin/codex-router.exe'}
            (resources/'application.json').write_text(json.dumps(manifest))
            self.assertEqual(layout.installed_path(resources,'bridge'),bridge.resolve())
            self.assertEqual(layout.installed_path(resources,'runtime'),runtime.resolve())
            for invalid in ('../outside.exe','other.exe','versions/elsewhere.exe'):
                (resources/'application.json').write_text(json.dumps(dict(manifest,bridge=invalid)))
                with self.assertRaises(ValueError):layout.installed_path(resources,'bridge')

    def fixture(self, folder):
        legacy=Path(folder)/'legacy';state=legacy/'state';state.mkdir(parents=True)
        wrapper=legacy/'dist/codex-router.exe';wrapper.parent.mkdir();wrapper.touch()
        previous={'value':None,'kind':1}
        record={'schema':1,'platform':'win32','status':'registered','wrapper':str(wrapper.resolve()),'previous':previous}
        (state/'desktop-integration.json').write_text(json.dumps(record))
        root=Path(folder)/'data';(root/'state').mkdir(parents=True)
        (root/'state/legacy-installation.json').write_text(json.dumps({'schema':1,'root':str(legacy)}))
        return legacy,root,record

    def test_imported_owned_connection_retains_original_environment_without_source_write(self):
        with tempfile.TemporaryDirectory() as folder:
            legacy,root,record=self.fixture(folder)
            before=(legacy/'state/desktop-integration.json').read_bytes()
            result=imported_connection(root,{'value':record['wrapper'],'kind':1})
            self.assertEqual(result['previous'],{'value':None,'kind':1})
            self.assertEqual((legacy/'state/desktop-integration.json').read_bytes(),before)

    def test_foreign_changed_or_wrong_platform_connections_are_not_adopted(self):
        for scenario in ('foreign','changed','platform'):
            with tempfile.TemporaryDirectory() as folder:
                legacy,root,record=self.fixture(folder)
                current={'value':record['wrapper'],'kind':1}
                if scenario=='changed':current['value']='foreign.exe'
                if scenario=='foreign':record['wrapper']='foreign.exe'
                if scenario=='platform':record['platform']='linux'
                (legacy/'state/desktop-integration.json').write_text(json.dumps(record))
                with patch('monitor_state.alive',return_value=True):
                    with self.assertRaises(DiscoveryError):imported_connection(root,current)

    def test_missing_provenance_does_not_override_foreign_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(imported_connection(folder,{'value':'foreign.exe','kind':1}))

    def test_active_owned_source_can_prepare_next_launch_without_source_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            legacy,root,record=self.fixture(folder)
            snapshot=legacy/'state/status-fixture.json'
            snapshot.write_text(json.dumps({'pid':os.getpid(),'heartbeat':time.time(),'events':[]}))
            source_receipt=legacy/'state/desktop-integration.json'
            before=(source_receipt.read_bytes(),snapshot.read_bytes())
            with patch('installation_migration.reject_active',side_effect=AssertionError('Offline guard must not gate next-launch registration')):
                result=imported_connection(root,{'value':record['wrapper'],'kind':1})
            self.assertEqual(result['previous'],record['previous'])
            self.assertEqual(before,(source_receipt.read_bytes(),snapshot.read_bytes()))

    def test_unverified_connection_returns_safe_code(self):
        with tempfile.TemporaryDirectory() as folder:
            legacy,root,record=self.fixture(folder)
            record['wrapper']='PRIVATE_SENTINEL'
            (legacy/'state/desktop-integration.json').write_text(json.dumps(record))
            with self.assertRaises(DiscoveryError) as error:
                imported_connection(root,{'value':'PRIVATE_SENTINEL','kind':1})
            self.assertEqual(error.exception.code,'source_connection_unverified')
            self.assertNotIn('PRIVATE_SENTINEL',str(error.exception))

    def test_reused_pid_does_not_block_transfer_or_change_source_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            legacy,root,record=self.fixture(folder)
            snapshot=legacy/'state/status-fixture.json'
            snapshot.write_text(json.dumps({'pid':123,'heartbeat':100,'events':[]}))
            before=snapshot.read_bytes()
            with patch('monitor_state.alive',return_value=True), \
                 patch('installation_migration.windows_process_started_at',return_value=200):
                reject_active(legacy/'state')
                self.assertEqual(imported_connection(root,{'value':record['wrapper'],'kind':1})['previous'],record['previous'])
            self.assertEqual(snapshot.read_bytes(),before)

    def test_stale_same_process_and_unknown_process_stay_blocked(self):
        for started in (99,100,100.5,None):
            with self.subTest(started=started), tempfile.TemporaryDirectory() as folder:
                state=Path(folder)/'state';state.mkdir()
                (state/'status-fixture.json').write_text(json.dumps({'pid':123,'heartbeat':100,'events':[]}))
                with patch('monitor_state.alive',return_value=True), \
                     patch('installation_migration.windows_process_started_at',return_value=started):
                    with self.assertRaises(MigrationError) as error:reject_active(state)
                self.assertEqual(error.exception.code,'active_bridge')

    def test_missing_or_invalid_heartbeat_cannot_prove_pid_reuse(self):
        for heartbeat in (None,False,'100',0,-1,float('nan'),float('inf')):
            with self.subTest(heartbeat=heartbeat), patch('installation_migration.windows_process_started_at') as query:
                self.assertFalse(snapshot_pid_reused({'pid':123,'heartbeat':heartbeat}))
                query.assert_not_called()

    @unittest.skipUnless(os.name=='nt','Windows native process creation time')
    def test_real_windows_process_creation_distinguishes_old_snapshot_from_live_bridge(self):
        started=windows_process_started_at(os.getpid())
        self.assertIsNotNone(started)
        self.assertLessEqual(started,time.time())
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state';state.mkdir()
            snapshot=state/'status-fixture.json'
            snapshot.write_text(json.dumps({'pid':os.getpid(),'heartbeat':started-10,'events':[]}))
            reject_active(state)
            snapshot.write_text(json.dumps({'pid':os.getpid(),'heartbeat':time.time(),'events':[]}))
            with self.assertRaises(MigrationError) as error:reject_active(state)
            self.assertEqual(error.exception.code,'active_bridge')

    @unittest.skipUnless(os.name=='nt','Windows named monitor mutex')
    def test_open_windows_monitor_blocks_import_without_touching_it(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state';state.mkdir()
            name='Local\\CodexRouterMonitor-'+hashlib.sha256(str(state.parent.resolve()).upper().encode()).hexdigest().upper()
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            handle=kernel.CreateMutexW(None,False,name);self.assertTrue(handle)
            try:
                with self.assertRaises(MigrationError) as error:reject_active(state)
                self.assertEqual(error.exception.code,'busy_source')
            finally:kernel.CloseHandle(handle)
            reject_active(state)


if __name__=='__main__':unittest.main()
