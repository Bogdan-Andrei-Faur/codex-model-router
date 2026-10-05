"""Offline release validation, non-blocking control and cancelled download custody."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from updates import (UpdateManager, UpdateError, architecture, candidate, fetch_release,
                     installer_name, valid_transport_url, version_key, SafeRedirect,
                     MAX_PACKAGE, LATEST, REPOSITORY)
from monitor_state import MonitorState

ROOT = Path(__file__).resolve().parents[1]
BODY = b'fixture installer bytes; never executed'


def release(platform='macos', arch='arm64', version='0.9.0'):
    name = installer_name(version, platform, arch)
    return {'tag_name': 'v' + version, 'draft': False, 'prerelease': False, 'assets': [{
        'name': name, 'state': 'uploaded', 'size': len(BODY),
        'digest': 'sha256:' + hashlib.sha256(BODY).hexdigest(),
        'browser_download_url': 'https://github.com/' + REPOSITORY + '/releases/download/v' + version + '/' + name}]}


class Response(io.BytesIO):
    headers = {}


class UpdateTests(unittest.TestCase):
    def manager(self, root, **kwargs):
        result = UpdateManager(root, '0.8.1', 'macos', arch='arm64',
                               fetcher=kwargs.pop('fetcher', release),
                               opener=kwargs.pop('opener', lambda _: Response(BODY)), **kwargs)
        self.addCleanup(result.close)
        return result

    def finish(self, model, operation):
        model.start(operation)
        model.future.result(timeout=3)
        return model.snapshot()

    def test_semver_numeric_and_prerelease_precedence(self):
        values = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta',
                  '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0', '1.0.1', '1.10.0']
        self.assertEqual(sorted(values, key=version_key), values)
        self.assertEqual(version_key('1.0.0+fixture'), version_key('1.0.0'))
        for invalid in ('01.0.0', '1.0', '1.0.0-01', '../../evil', '1.0.0\n'):
            with self.assertRaises(UpdateError): version_key(invalid)

    def test_each_platform_requires_exact_architecture_package(self):
        for platform in ('macos', 'windows', 'linux'):
            for arch in ('arm64', 'x64'):
                version, asset = candidate(release(platform, arch), '0.8.1', platform, arch)
                self.assertEqual(version, '0.9.0')
                self.assertTrue(asset['name'].startswith('codex-model-router-'))
                self.assertIsNone(candidate(release(platform, arch), '0.8.1', platform, 'x86')[1])
        self.assertEqual(architecture('aarch64'), 'arm64')
        self.assertEqual(architecture('AMD64'), 'x64')
        self.assertIsNone(architecture('riscv64'))

    def test_downgrade_build_metadata_and_prerelease(self):
        self.assertIsNone(candidate(release(version='0.8.0'), '0.8.1', 'macos', 'arm64')[1])
        self.assertIsNone(candidate(release(version='0.8.1'), '0.8.1+local', 'macos', 'arm64')[1])
        for field in ('draft', 'prerelease'):
            data=release(); data[field]=True
            with self.assertRaises(UpdateError): candidate(data, '0.8.1', 'macos', 'arm64')

    def test_rejects_missing_digest_duplicate_foreign_repo_and_oversize(self):
        for changes in ({'digest': None}, {'size': True}, {'size': MAX_PACKAGE+1}, {'state': 'new'},
                        {'browser_download_url': 'https://github.com/other/repo/releases/download/a/pkg'}):
            data=release(); data['assets'][0].update(changes)
            with self.assertRaises(UpdateError): candidate(data, '0.8.1', 'macos', 'arm64')
        data=release(); data['assets']*=2
        with self.assertRaises(UpdateError): candidate(data, '0.8.1', 'macos', 'arm64')

    def test_redirects_require_tls_allowed_host_and_no_credentials(self):
        self.assertTrue(valid_transport_url(LATEST))
        for url in ('http://github.com/x', 'https://github.com.evil.test/x', 'https://u:p@github.com/x',
                    'https://localhost/x', 'https://github.com:bad/x', 'file:///tmp/x', 'https://github.com/x#bad'):
            self.assertFalse(valid_transport_url(url))
            with self.assertRaises(UpdateError):
                SafeRedirect().redirect_request(urllib.request.Request(LATEST), None, 302, '', {}, url)

    def test_http_404_is_unknown_not_up_to_date_and_raw_errors_never_projected(self):
        error=urllib.error.HTTPError(LATEST, 404, 'PRIVATE_RESPONSE', {}, None)
        with patch('updates.open_url', side_effect=error):
            with self.assertRaises(UpdateError) as caught: fetch_release()
        self.assertEqual(caught.exception.code, 'release_unavailable')
        with tempfile.TemporaryDirectory() as folder:
            model=self.manager(folder,fetcher=lambda: (_ for _ in ()).throw(RuntimeError('PRIVATE_RESPONSE')))
            state=self.finish(model,'check')
            self.assertEqual(state['status'],'error'); self.assertIsNone(state['latestVersion'])
            self.assertNotIn('PRIVATE_RESPONSE',json.dumps(state))

    def test_valid_download_checks_integrity_and_never_claims_install_or_authenticity(self):
        with tempfile.TemporaryDirectory() as folder:
            model=self.manager(folder)
            self.assertTrue(self.finish(model,'check')['canDownload'])
            state=self.finish(model,'download')
            self.assertEqual(state['status'],'downloaded'); self.assertFalse(state['canInstall'])
            directory=Path(folder)/'state/updates'
            self.assertEqual((directory/installer_name('0.9.0','macos','arm64')).read_bytes(), BODY)
            receipt=json.loads((directory/'staged.json').read_text())
            self.assertEqual(receipt['sha256'],hashlib.sha256(BODY).hexdigest())
            self.assertNotIn('url',receipt); self.assertEqual(list(directory.glob('.download-*')),[])

    def test_bad_bytes_or_content_length_leave_no_installer_or_temporary(self):
        for data, length in ((b'X'*len(BODY),None),(BODY+b'excess',None),(BODY,'999')):
            with tempfile.TemporaryDirectory() as folder:
                response=Response(data)
                response.headers={} if length is None else {'Content-Length':length}
                model=self.manager(folder,opener=lambda _: response)
                self.finish(model,'check'); state=self.finish(model,'download')
                self.assertEqual(state['status'],'error')
                self.assertEqual(list((Path(folder)/'state/updates').iterdir()),[])

    def test_cancel_pending_check_discards_late_result_and_does_not_block_snapshot(self):
        entered=threading.Event(); done=threading.Event()
        def pending(): entered.set(); done.wait(3); return release()
        with tempfile.TemporaryDirectory() as folder:
            model=self.manager(folder,fetcher=pending)
            model.start('check'); self.assertTrue(entered.wait(1))
            self.assertEqual(model.snapshot()['status'],'checking')
            model.start('cancel'); done.set(); model.future.result(timeout=3)
            self.assertEqual(model.snapshot()['status'],'cancelled')
            self.assertIsNone(model.snapshot()['latestVersion']); self.assertIsNone(model.package)

    def test_cancel_active_download_cleans_partial_and_preserves_user_state(self):
        entered=threading.Event(); done=threading.Event()
        class Pending(Response):
            def read(self, count): entered.set(); done.wait(3); return super().read(count)
        with tempfile.TemporaryDirectory() as folder:
            user=Path(folder)/'config.local.json'; user.write_text('{"unchanged":true}')
            model=self.manager(folder,opener=lambda _: Pending(BODY))
            self.finish(model,'check'); model.start('download'); self.assertTrue(entered.wait(1))
            model.start('cancel'); done.set(); model.future.result(timeout=3)
            self.assertEqual(model.snapshot()['status'],'cancelled')
            self.assertEqual(list((Path(folder)/'state/updates').iterdir()),[])
            self.assertEqual(user.read_text(),'{"unchanged":true}')

    def test_daily_checks_are_opt_in_and_throttled_even_after_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[]
            def fetch(): calls.append(1); raise UpdateError('release_unavailable')
            model=self.manager(folder,fetcher=fetch)
            model.maybe_check(False); self.assertIsNone(model.future)
            model.maybe_check(True); model.future.result(timeout=3)
            model.maybe_check(True); self.assertEqual(calls,[1])

    def test_preview_and_shared_action_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            for platform in ('macos','windows','linux'):
                model=MonitorState(folder,ROOT,preview=True,platform=platform)
                try:
                    with patch.object(model.updater,'start') as start:
                        with self.assertRaises(ValueError): model.action({'action':'update','value':'check'})
                        model.payload(False); start.assert_not_called()
                        self.assertFalse(model.payload(False)['updates']['canInstall'])
                finally: model.close()
            model=MonitorState(folder,ROOT,platform='macos')
            try:
                with patch.object(model.updater,'start',return_value='checking') as start:
                    self.assertEqual(model.action({'action':'update','value':'check'}),'checking')
                    start.assert_called_once_with('check')
                (Path(folder)/'config.local.json').write_text('{"enabled":true}')
                model.configure('updates_auto_check',True)
                with patch.object(model.updater,'maybe_check') as check:
                    model.payload(False); check.assert_called_once_with(True)
            finally: model.close()
