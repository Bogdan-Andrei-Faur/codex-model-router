"""Application transaction faults use disposable apps, never an installed monitor."""
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from codex_model_router.update_install import (replace_and_confirm, recover_interrupted,
    app_info, installed_applier, APP_NAME, APP_ID, copy_verified, validate_tree,
    run_helper, clean_environment, MacApplier)
from codex_model_router.update_trust import TrustError
import hashlib


class UpdateInstallTests(unittest.TestCase):
    def app(self, parent, name, version):
        p=parent/name;(p/'Contents').mkdir(parents=True)
        (p/'Contents/Info.plist').write_bytes(plistlib.dumps(dict(CFBundleIdentifier=APP_ID,
            CFBundleExecutable='codex-monitor-mac',RouterPackaged=True,CFBundleShortVersionString=version)))
        (p/'owner').write_text(version);return p

    def test_success_keeps_previous_and_launch_failure_restores_it(self):
        for ok in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);app=self.app(root,APP_NAME,'1.0.0')
                staged=self.app(root,'.router-new-'+('a'*32)+'.app','1.1.0')
                previous=root/('.router-previous-'+('a'*32)+'.app')
                launched=[];records=[]
                class Child:
                    stopped=False
                    def poll(self):return 1 if self.stopped else None
                    def terminate(self):self.stopped=True
                    def wait(self,timeout):return 0
                def launch(path):launched.append(app_info(path)['CFBundleShortVersionString']);return Child()
                result=replace_and_confirm(app,staged,previous,launch,lambda child:ok,records.append)
                self.assertEqual(result,'completed' if ok else 'rolled_back')
                self.assertEqual(app_info(app)['CFBundleShortVersionString'],'1.1.0' if ok else '1.0.0')
                self.assertEqual(launched,['1.1.0'] if ok else ['1.1.0','1.0.0'])
                self.assertEqual((previous if ok else staged).joinpath('owner').read_text(),'1.0.0' if ok else '1.1.0')

    def test_crash_between_renames_and_before_confirmation_can_be_recovered(self):
        for new_moved in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);app=self.app(root,APP_NAME,'1.0.0');staged=self.app(root,'.router-new-'+('b'*32)+'.app','1.1.0')
                previous=root/('.router-previous-'+('b'*32)+'.app');app.rename(previous)
                if new_moved:staged.rename(app)
                recover_interrupted(app,staged,previous,'1.1.0','1.0.0')
                self.assertEqual(app_info(app)['CFBundleShortVersionString'],'1.0.0')
                self.assertTrue(staged.exists());self.assertFalse(previous.exists())

    def test_copy_rechecks_exact_bytes_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'package';source.write_bytes(b'fixture')
            package=dict(size=7,sha256=hashlib.sha256(b'fixture').hexdigest())
            copy_verified(source,root/'ok',package)
            source.write_bytes(b'changed')
            with self.assertRaises(TrustError):copy_verified(source,root/'bad',package)
            link=root/'link'
            try:link.symlink_to(source)
            except OSError:self.skipTest('Symlinks unavailable')
            with self.assertRaises(TrustError):copy_verified(link,root/'bad-link',package)

    def test_source_other_platforms_and_external_bundle_links_are_not_eligible(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for platform in ('macos','windows','linux'):self.assertIsNone(installed_applier(root,root,platform))
            app=self.app(root,APP_NAME,'1.0.0');external=root/'outside';external.write_text('preserve')
            try:(app/'escape').symlink_to(external)
            except OSError:self.skipTest('Symlinks unavailable')
            with self.assertRaises(TrustError):validate_tree(app)

    def test_completed_login_job_only_removes_its_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);token='c'*32;job=root/'state/updates/jobs'/token;job.mkdir(parents=True)
            resources=job/APP_NAME/'Contents/Resources';resources.mkdir(parents=True)
            (job/'operation.json').write_text(json.dumps(dict(schema=1,token=token,phase='completed')))
            agent=root/'recovery.plist';agent.write_text('fixture')
            with patch('codex_model_router.update_install.sys.platform','darwin'),patch('codex_model_router.update_install.recovery_agent',return_value=agent):
                run_helper(root,resources,token)
            self.assertFalse(agent.exists());self.assertTrue((job/'operation.json').exists())

    def test_frozen_child_environment_and_downgrade_preflight(self):
        with patch.dict('os.environ',{'_PYI_APPLICATION_HOME_DIR':'old','DYLD_LIBRARY_PATH':'old','PYTHONPATH':'old','PERSONAL_CODEX_ROUTER_ROOT':'old'}):
            env=clean_environment()
        self.assertNotIn('_PYI_APPLICATION_HOME_DIR',env);self.assertNotIn('DYLD_LIBRARY_PATH',env)
        self.assertNotIn('PYTHONPATH',env);self.assertNotIn('PERSONAL_CODEX_ROUTER_ROOT',env)
        self.assertEqual(env['PYINSTALLER_RESET_ENVIRONMENT'],'1')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);app=self.app(root,APP_NAME,'1.1.0')
            applier=MacApplier(root/'data',app/'Contents/Resources')
            for version in ('1.0.0','1.1.0'):
                with self.assertRaises(TrustError):applier.prepare(None,{'version':version},None,None)
