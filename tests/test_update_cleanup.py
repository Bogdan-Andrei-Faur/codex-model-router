"""Retention tests use disposable apps and never inspect owner data/processes."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from codex_model_router.update_cleanup import cleanup_macos
from codex_model_router.update_install import APP_NAME, APP_ID
from codex_model_router.updates import UpdateManager


@unittest.skipIf(os.name == 'nt', 'Mac filesystem retention uses Unix ownership and locks')
class UpdateCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'data'
        self.jobs = self.root / 'state/updates/jobs'
        self.jobs.mkdir(parents=True)
        self.apps = self.base / 'Applications'
        self.apps.mkdir()
        self.app = self.bundle(self.apps / APP_NAME, '1.2.0')
        for target, replacement in (
            ('codex_model_router.update_cleanup._process_commands', lambda: ['unrelated-process']),
            ('codex_model_router.update_cleanup.recovery_agent', lambda token: self.base / (token + '.plist')),
        ):
            p = patch(target, replacement); p.start(); self.addCleanup(p.stop)

    def bundle(self, path, version):
        (path / 'Contents').mkdir(parents=True)
        (path / 'Contents/Info.plist').write_bytes(plistlib.dumps(dict(
            CFBundleIdentifier=APP_ID, CFBundleExecutable='codex-monitor-mac', RouterPackaged=True,
            CFBundleShortVersionString=version, RouterBuildId='build-' + version)))
        (path / 'payload').write_text(version)
        return path

    def job(self, digit, old, new, phase='completed'):
        token = digit * 32
        job = self.jobs / token; job.mkdir()
        package = dict(name='codex-model-router-' + new + '-macos-arm64.pkg', version=new,
                       size=7, sha256=hashlib.sha256(b'package').hexdigest())
        op = dict(schema=1, token=token, app=str(self.app), phase=phase,
                  oldVersion=old, oldBuild='build-' + old, package=package)
        (job / 'operation.json').write_text(json.dumps(op))
        (job / 'signature.json').write_text('retain public signature')
        self.bundle(job / APP_NAME, old)
        for name in ('expanded', 'rechecked'):
            (job / name).mkdir(); (job / name / 'payload').write_text('temporary')
        for name in (package['name'], 'checked-' + package['name']):
            (job / name).write_bytes(b'package')
        previous = self.bundle(self.apps / ('.router-previous-' + token + '.app'), old)
        return job, previous

    def clean(self, **kwargs):
        return cleanup_macos(self.root, self.app, **kwargs)

    def test_multiple_upgrades_keep_only_latest_previous_and_small_receipts(self):
        older, old_backup = self.job('a', '1.0.0', '1.1.0')
        latest, keep = self.job('b', '1.1.0', '1.2.0')
        cache = self.root / 'state/updates/codex-model-router-1.2.0-macos-arm64.pkg'
        cache.write_bytes(b'package')
        owner = self.root / 'config.local.json'; owner.write_text('owner config')
        extra = latest / 'unknown'; extra.write_text('preserve')
        foreign = self.bundle(self.apps / '.router-previous-cccccccccccccccccccccccccccccccc.app', '0.1.0')
        self.assertEqual(self.clean(dry_run=True)['status'], 'planned')
        self.assertTrue(old_backup.exists())
        result = self.clean()
        self.assertEqual(result['status'], 'cleaned')
        self.assertEqual(result['previous_retained'], 1)
        self.assertFalse(old_backup.exists()); self.assertTrue(keep.exists())
        self.assertTrue(foreign.exists()); self.assertTrue(extra.exists())
        self.assertEqual(owner.read_text(), 'owner config')
        self.assertFalse(cache.exists()); self.assertTrue(self.app.exists())
        for job in (older, latest):
            self.assertTrue((job / 'operation.json').exists())
            self.assertTrue((job / 'signature.json').exists())
            self.assertFalse((job / APP_NAME).exists())
        self.assertEqual(self.clean()['removed'], 0)

    def test_unconfirmed_or_pending_jobs_defer_without_partial_deletion(self):
        older, backup = self.job('a', '1.0.0', '1.1.0')
        latest, keep = self.job('b', '1.1.0', '1.2.0', 'confirming')
        self.assertEqual(self.clean()['status'], 'deferred')
        self.assertTrue(backup.exists()); self.assertTrue((older / APP_NAME).exists())
        (latest / 'operation.json').write_text('{broken')
        self.assertEqual(self.clean()['removed'], 0)
        self.assertTrue(keep.exists())

    def test_live_helper_or_recovery_registration_defers_cleanup(self):
        job, keep = self.job('b', '1.1.0', '1.2.0')
        with patch('codex_model_router.update_cleanup._process_commands', return_value=[str(job / APP_NAME) + '/runtime']):
            self.assertEqual(self.clean()['removed'], 0)
        agent = self.base / ('b' * 32 + '.plist'); agent.touch()
        self.assertEqual(self.clean()['status'], 'deferred')
        self.assertTrue((job / APP_NAME).exists()); self.assertTrue(keep.exists())

    def test_inventory_failure_does_not_delete(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        with patch('codex_model_router.update_cleanup._process_commands', side_effect=OSError):
            self.assertEqual(self.clean()['removed'], 0)
        self.assertTrue((job / APP_NAME).exists())

    def test_replacement_lock_blocks_cleanup(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        with patch('codex_model_router.update_cleanup.file_lock', side_effect=TimeoutError):
            self.assertEqual(self.clean()['removed'], 0)
        self.assertTrue((job / APP_NAME).exists())

    def test_top_level_links_and_foreign_app_receipts_are_preserved(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        outside = self.base / 'important'; outside.mkdir()
        (outside / 'value').write_text('keep')
        import shutil
        shutil.rmtree(job / 'expanded'); (job / 'expanded').symlink_to(outside)
        self.assertEqual(self.clean()['status'], 'deferred')
        self.assertEqual((outside / 'value').read_text(), 'keep')
        self.assertTrue((job / APP_NAME).exists())
        (job / 'expanded').unlink()
        op = json.loads((job / 'operation.json').read_text()); op['app'] = str(outside)
        (job / 'operation.json').write_text(json.dumps(op))
        self.assertEqual(self.clean()['removed'], 0)

    def test_inner_symlink_target_is_never_traversed(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        outside = self.base / 'important'; outside.mkdir()
        (outside / 'value').write_text('keep')
        (job / 'expanded/link').symlink_to(outside)
        self.assertEqual(self.clean()['status'], 'cleaned')
        self.assertEqual((outside / 'value').read_text(), 'keep')

    def test_newer_download_or_tampered_backup_stops_all_deletion(self):
        job, backup = self.job('b', '1.1.0', '1.2.0')
        newer = self.root / 'state/updates/codex-model-router-1.3.0-macos-arm64.pkg'
        newer.write_bytes(b'preserve download')
        info = backup / 'Contents/Info.plist'; d = plistlib.loads(info.read_bytes())
        d['RouterBuildId'] = 'foreign'; info.write_bytes(plistlib.dumps(d))
        self.assertEqual(self.clean()['removed'], 0)
        d['RouterBuildId'] = 'build-1.1.0'; info.write_bytes(plistlib.dumps(d))
        self.assertEqual(self.clean()['status'], 'cleaned')
        self.assertTrue(newer.exists())

    def test_package_path_cannot_escape_job(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        op = json.loads((job / 'operation.json').read_text())
        op['package']['name'] = '../../owner-file'
        (job / 'operation.json').write_text(json.dumps(op))
        self.assertEqual(self.clean()['removed'], 0)

    def test_malformed_version_is_a_safe_deferral(self):
        job, _ = self.job('b', '1.1.0', '1.2.0')
        op = json.loads((job / 'operation.json').read_text())
        op['package']['version'] = 'corrupt'
        (job / 'operation.json').write_text(json.dumps(op))
        self.assertEqual(self.clean()['status'], 'deferred')
        self.assertTrue((job / APP_NAME).exists())

    def test_no_valid_backup_defers_instead_of_dropping_recovery_material(self):
        job, backup = self.job('b', '1.1.0', '1.2.0')
        import shutil
        shutil.rmtree(backup)
        self.assertEqual(self.clean()['status'], 'no_recovery_copy')
        self.assertTrue((job / APP_NAME).exists())

    def test_maintenance_is_off_thread_local_and_throttled_without_auto_check(self):
        import threading
        threads = []
        class Applier:
            def maintenance(self): threads.append(threading.get_ident())
        updater = UpdateManager(self.root, '1.2.0', 'macos', applier=Applier())
        self.addCleanup(updater.close)
        updater.maybe_check(False); updater.future.result(timeout=3)
        updater.maybe_check(False)
        self.assertEqual(len(threads), 1)
        self.assertNotEqual(threads[0], threading.get_ident())
        self.assertEqual(updater.snapshot()['status'], 'idle')


if __name__ == '__main__':
    unittest.main()
