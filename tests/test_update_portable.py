"""Disposable transaction fixtures; never install software or touch owner state."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from codex_model_router import update_portable as u
from codex_model_router.update_trust import TrustError
from codex_model_router.update_install import installed_applier


class PortableUpdateTests(unittest.TestCase):
    def resources(self, base, version='1.0.0', platform='linux'):
        resources = base/'Resources'; resources.mkdir(parents=True)
        (resources/'VERSION').write_text(version)
        (resources/'application.json').write_text(json.dumps(dict(schema=1,
            layout='linux-deb-v1' if platform=='linux' else 'windows-install-v1',
            managedUpdateProtocol=1, runtime='bin/runtime', monitor='bin/monitor')))
        (base/'bin').mkdir(); (base/'bin/runtime').touch(); (base/'bin/monitor').touch()
        return resources

    def fixture(self, root, platform='linux', phase='prepared'):
        token='a'*32; job=root/'state/updates/jobs'/token;job.mkdir(parents=True)
        old=self.resources(root/'application'/'versions'/'1.0.0-123456789abcdef0',platform=platform)
        worker=self.resources(job/'worker',platform=platform)
        package=dict(name='package.exe' if platform=='windows' else 'package.deb',version='1.1.0',size=7,sha256=hashlib.sha256(b'package').hexdigest())
        (job/package['name']).write_bytes(b'package')
        app=root/'application' if platform=='windows' else None
        previous={'schema':1,'versionDirectory':old.parent.name} if app else None
        if app: (app/'active.json').write_text(json.dumps(previous))
        operation=dict(schema=1,token=token,platform=platform,package=package,application=str(app) if app else None,oldResources=str(old),previous=previous,phase=phase)
        (job/'operation.json').write_text(json.dumps(operation));(job/'signature.json').write_text('{}')
        return token,job,old,worker

    def helper(self, root, platform='linux', success=True, phase='prepared', cancel=False, installer_error=False):
        token,job,old,worker=self.fixture(root,platform,phase)
        launched=[]
        if cancel:(job/'cancel').touch()
        def extract(_archive,destination):return self.resources(destination,'1.1.0')
        def run(command,**kwargs):
            if command[0].endswith('package.exe'):
                if installer_error:raise subprocess.CalledProcessError(1,command)
                target=self.resources(root/'application/versions/1.1.0-fedcba9876543210','1.1.0','windows')
                (root/'application/active.json').write_text(json.dumps({'versionDirectory':target.parent.name}))
            return Mock(returncode=0)
        def launch(command,**kwargs):
            launched.append(command)
            ack=any(a.startswith('--update-ready=') for a in command)
            if ack and success:(job/'ready').touch()
            return Mock(poll=lambda: None if success else 1)
        with patch.object(u.sys,'platform','win32' if platform=='windows' else 'linux'), \
             patch.object(u,'register_recovery'),patch.object(u,'reject_active'),patch.object(u,'windows_installer_running',return_value=False), \
             patch.object(u,'verify'),patch.object(u,'load_keys'), \
             patch.object(u,'extract_linux',side_effect=extract), \
             patch.object(u.subprocess,'run',side_effect=run),patch.object(u.subprocess,'Popen',side_effect=launch):
            if not success and phase=='prepared' and not cancel or installer_error:
                with self.assertRaises((TrustError,subprocess.CalledProcessError)):u.run_helper(root,worker,token)
            else:u.run_helper(root,worker,token)
        return job,old,launched

    def test_windows_recovery_registration_is_bounded_and_uses_stable_dispatch(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve(); token,job,old,worker=self.fixture(root,'windows')
            registry=Mock();registry.CreateKey.return_value.__enter__=Mock(return_value='fixture-key')
            registry.CreateKey.return_value.__exit__=Mock(return_value=False)
            with patch.dict(sys.modules,winreg=registry),patch.object(u.sys,'platform','win32'),patch.dict(os.environ,LOCALAPPDATA=str(root.parent)):
                u.register_recovery(root,token,['unused long copied runtime'])
                line=registry.SetValueEx.call_args.args[-1]
                self.assertIn('--recover-update',line);self.assertNotIn('/worker/',line)
                self.assertLessEqual(len(line.encode('utf-16-le'))//2,260)
                registry.SetValueEx.reset_mock()
                operation=u.read(job/'operation.json');operation['application']='x'*270
                u.atomic_json(job/'operation.json',operation)
                with self.assertRaisesRegex(TrustError,'recovery_path_too_long'):
                    u.register_recovery(root,token,[])
                registry.SetValueEx.assert_not_called()

    def test_real_signed_bytes_survive_prepare_and_helper_boundary(self):
        from tools.packaging.release_manifest import sign
        from codex_model_router.updates import architecture, installer_name
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.skipTest('cryptography unavailable')
        import base64
        for platform in ('linux', 'windows'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve()
                resources=self.resources(root/'application/versions/1.0.0-123456789abcdef0',platform=platform)
                key=Ed25519PrivateKey.generate()
                public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
                (resources/'assets').mkdir()
                (resources/'assets/update-trust.json').write_text(json.dumps(dict(schema=1,keys={
                    hashlib.sha256(public).hexdigest():base64.b64encode(public).decode()})))
                archive=root/installer_name('1.1.0',platform,architecture());archive.write_bytes(b'package')
                package=dict(version='1.1.0',name=archive.name,size=7,sha256=hashlib.sha256(b'package').hexdigest())
                envelope=sign(key,'1.1.0',[(platform+'/'+architecture(),archive)])
                def handoff(command,**kwargs):
                    job=root/'state/updates/jobs'/command[-1]
                    self.assertEqual((job/'signature.json').read_bytes(),envelope)
                    (job/'ready-to-close').touch()
                    return Mock(poll=lambda:None)
                with patch.object(u,'reject_active'),patch.object(u,'register_recovery'),patch.object(u.subprocess,'Popen',side_effect=handoff):
                    self.assertTrue(u.PortableApplier(root,resources,platform).prepare(archive,package,envelope,threading.Event()))
                job=next((root/'state/updates/jobs').iterdir())
                # Real cryptographic verification in the copied worker; stop
                # only at the first OS-specific operation after authentication.
                with patch.object(u.sys,'platform','linux' if platform=='linux' else 'win32'),patch.object(u,'register_recovery'),patch.object(u,'wait_monitor',return_value=False),patch.object(u,'extract_linux',side_effect=RuntimeError('authenticated')),patch.object(u.subprocess,'Popen'):
                    if platform=='linux':
                        with self.assertRaisesRegex(RuntimeError,'authenticated'):
                            u.run_helper(root,job/'worker/Resources',job.name)
                    else:
                        u.run_helper(root,job/'worker/Resources',job.name)
                        self.assertEqual(u.read(job/'operation.json')['phase'],'cancelled')

    def test_success_and_launch_failure_restore_each_platform(self):
        for platform in ('linux','windows'):
            for success in (True,False):
                with self.subTest(platform=platform,success=success),tempfile.TemporaryDirectory() as folder:
                    root=Path(folder).resolve();(root/'config.local.json').write_text('private fixture')
                    job,old,launched=self.helper(root,platform,success)
                    self.assertEqual(u.read(job/'operation.json')['phase'],'completed' if success else 'rolled_back')
                    self.assertEqual((root/'config.local.json').read_text(),'private fixture')
                    self.assertEqual(len(launched),1 if success else 2)
                    if platform=='linux':self.assertEqual(u.selection_path(root).exists(),success)
                    else:self.assertTrue(u.read(root/'application/active.json')['versionDirectory'].startswith('1.1.0' if success else '1.0.0'))

    def test_interrupted_commit_restores_selection_without_installer(self):
        for platform in ('linux','windows'):
            for phase in ('committing','confirming'):
                with tempfile.TemporaryDirectory() as folder:
                    job,old,launched=self.helper(Path(folder).resolve(),platform,phase=phase)
                    self.assertEqual(u.read(job/'operation.json')['phase'],'rolled_back')
                    self.assertEqual(len(launched),1)

    def test_cancel_leaves_selection_and_never_launches(self):
        for platform in ('linux','windows'):
            with tempfile.TemporaryDirectory() as folder:
                job,old,launched=self.helper(Path(folder).resolve(),platform,cancel=True)
                self.assertEqual(u.read(job/'operation.json')['phase'],'cancelled');self.assertEqual(launched,[])

    def test_installer_failure_restores_windows_previous_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            job,old,launched=self.helper(Path(folder).resolve(),'windows',installer_error=True)
            self.assertEqual(u.read(job/'operation.json')['phase'],'rolled_back')
            self.assertEqual(len(launched),1)

    def test_bad_bytes_and_signature_never_close_monitor(self):
        for signature in (False,True):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve();token,job,old,worker=self.fixture(root)
                if not signature:(job/'package.deb').write_bytes(b'altered')
                with patch.object(u.sys,'platform','linux'),patch.object(u,'register_recovery'),patch.object(u,'load_keys'), \
                     patch.object(u,'verify',side_effect=TrustError('invalid_signature') if signature else None), \
                     patch.object(u,'monitor_lease',side_effect=TimeoutError),patch.object(u.subprocess,'Popen') as popen:
                    with self.assertRaises(TrustError):u.run_helper(root,worker,token)
                    self.assertFalse((job/'ready-to-close').exists());popen.assert_not_called()

    def test_terminal_replay_does_not_reinstall(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();token,job,old,worker=self.fixture(root,phase='completed')
            with patch.object(u.sys,'platform','linux'),patch.object(u,'register_recovery') as cleanup,patch.object(u.subprocess,'run') as run:
                u.run_helper(root,worker,token);run.assert_not_called();cleanup.assert_called_once()

    def test_recovery_never_overwrites_a_different_installation(self):
        for platform in ('linux','windows'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve();token,job,old,worker=self.fixture(root,platform,phase='committing')
                pointer=root/'application/active.json' if platform=='windows' else u.selection_path(root)
                value={'versionDirectory':'2.0.0-123456789abcdef0'} if platform=='windows' else {'token':'c'*32}
                u.atomic_json(pointer,value)
                with patch.object(u.sys,'platform','win32' if platform=='windows' else 'linux'),patch.object(u,'reject_active'),patch.object(u,'register_recovery'),patch.object(u.subprocess,'Popen') as popen:
                    with self.assertRaises(TrustError):u.run_helper(root,worker,token)
                    self.assertEqual(u.read(pointer),value);popen.assert_not_called()

    def test_windows_recovery_waits_for_surviving_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();token,job,old,worker=self.fixture(root,'windows',phase='committing')
            with patch.object(u.sys,'platform','win32'),patch.object(u,'reject_active'),patch.object(u,'windows_installer_running',return_value=True),patch.object(u.subprocess,'Popen') as popen:
                with self.assertRaises(TrustError):u.run_helper(root,worker,token)
                self.assertEqual(u.read(job/'operation.json')['phase'],'committing');popen.assert_not_called()

    def test_linux_selection_newer_baseline_and_untrusted_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();base=self.resources(root/'system')
            target=self.resources(root/'state/updates/jobs'/('b'*32)/'candidate','1.1.0')
            u.atomic_json(u.selection_path(root),{'token':'b'*32})
            self.assertEqual(u.linux_selected(root,base),target)
            (base/'VERSION').write_text('1.2.0');self.assertEqual(u.linux_selected(root,base),base)
            u.atomic_json(u.selection_path(root),{'token':'../../bad'})
            with self.assertRaises(TrustError):u.linux_selected(root,base)

    def test_tar_traversal_links_devices_and_setuid_rejected_before_extraction(self):
        for kind in ('traversal','symlink','device','setuid'):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                def unpack(command,stdout,**kwargs):
                    with tarfile.open(fileobj=stdout,mode='w') as tar:
                        entry=tarfile.TarInfo('../escape' if kind=='traversal' else './usr/lib/codex-model-router/bad')
                        if kind=='symlink':entry.type=tarfile.SYMTYPE;entry.linkname='/etc'
                        if kind=='device':entry.type=tarfile.CHRTYPE
                        if kind=='setuid':entry.mode=0o4755
                        tar.addfile(entry)
                with patch.object(u.subprocess,'run',side_effect=unpack):
                    with self.assertRaises(TrustError):u.extract_linux(root/'fake.deb',root/'candidate')
                self.assertFalse((root/'candidate/bad').exists())

    def test_windows_command_cannot_restart_or_close_other_apps(self):
        command=u.windows_install_command(Path('C:/space here/setup.exe'),Path('C:/app here'))
        for flag in ('/NORESTART','/NOCLOSEAPPLICATIONS','/NORESTARTAPPLICATIONS','/RESTARTEXITCODE=3010'):self.assertIn(flag,command)
        self.assertEqual(command[-1],'/DIR=C:/app here')

    def test_adapter_requires_protocol_and_actual_host(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();resources=self.resources(root/'base')
            with patch.object(u.sys,'platform','linux'):
                self.assertIsNotNone(installed_applier(root,resources,'linux'))
                value=u.read(resources/'application.json');value.pop('managedUpdateProtocol')
                u.atomic_json(resources/'application.json',value)
                self.assertIsNone(installed_applier(root,resources,'linux'))


if __name__=='__main__':unittest.main()
