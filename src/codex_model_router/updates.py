"""Shared release discovery, authenticated staging and installed update handoff.

Native installer trust, apply/rollback and managed relaunch are a separate gate.
Only the canonical repository is queried; no config, prompts, tokens or keys leave
this process. Network work is asynchronous and update state is projected safely.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform as host_platform
import re
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from codex_model_router.storage.state_store import atomic_json

REPOSITORY = 'Bogdan-Andrei-Faur/codex-model-router'
LATEST = 'https://api.github.com/repos/' + REPOSITORY + '/releases/latest'
MAX_METADATA = 1024 * 1024
MAX_PACKAGE = 512 * 1024 * 1024
DOWNLOAD_SECONDS = 180
VERSION = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$')


class UpdateError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def version_key(value):
    if not isinstance(value, str) or len(value) > 128:
        raise UpdateError('invalid_release')
    match = VERSION.fullmatch(value)
    if not match:
        raise UpdateError('invalid_release')
    major, minor, patch, pre, _build = match.groups()
    identifiers = []
    for token in (pre or '').split('.') if pre else []:
        if token.isdigit():
            if len(token) > 1 and token[0] == '0':
                raise UpdateError('invalid_release')
            identifiers.append((0, int(token)))
        else:
            identifiers.append((1, token))
    return (int(major), int(minor), int(patch), 0 if pre else 1, tuple(identifiers))


def architecture(machine=None):
    return {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64',
            'x86': 'x86', 'i386': 'x86', 'i686': 'x86'}.get((machine or host_platform.machine()).lower())


def installer_name(version, platform, arch):
    if platform not in ('macos', 'windows', 'linux') or arch not in ('x64', 'arm64', 'x86'):
        raise UpdateError('unsupported_platform')
    version_key(version)
    suffix = {'macos': '.pkg', 'windows': '-setup.exe', 'linux': '.deb'}[platform]
    return 'codex-model-router-' + version + '-' + platform + '-' + arch + suffix


def valid_transport_url(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.scheme == 'https' and parsed.port in (None, 443) and not parsed.username
                and not parsed.password and not parsed.fragment and parsed.hostname in ('api.github.com', 'github.com',
                'objects.githubusercontent.com', 'release-assets.githubusercontent.com', 'github-releases.githubusercontent.com'))
    except (ValueError, TypeError):
        return False


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        if not valid_transport_url(url):
            raise UpdateError('unsafe_download')
        return super().redirect_request(request, fp, code, message, headers, url)


def open_url(url):
    if not valid_transport_url(url):
        raise UpdateError('unsafe_download')
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json' if url == LATEST else 'application/octet-stream',
                                                  'User-Agent': 'codex-model-router-updates', 'X-GitHub-Api-Version': '2022-11-28'})
    response = urllib.request.build_opener(SafeRedirect()).open(request, timeout=10)
    if not valid_transport_url(response.geturl()):
        response.close()
        raise UpdateError('unsafe_download')
    return response


def fetch_release():
    try:
        with open_url(LATEST) as response:
            body = response.read(MAX_METADATA + 1)
        if len(body) > MAX_METADATA:
            raise UpdateError('invalid_release')
        data = json.loads(body)
        if not isinstance(data, dict):
            raise UpdateError('invalid_release')
        return data
    except urllib.error.HTTPError as error:
        # 404 may mean private repo, missing release, or no anonymous access.
        raise UpdateError('release_unavailable' if error.code == 404 else 'rate_limited' if error.code in (403, 429) else 'network_error') from None
    except (OSError, ValueError):
        raise UpdateError('network_error') from None


def candidate(release, installed, platform, arch):
    if release.get('draft') is not False or release.get('prerelease') is not False:
        raise UpdateError('invalid_release')
    tag = release.get('tag_name')
    if not isinstance(tag, str):
        raise UpdateError('invalid_release')
    version = tag[1:] if tag.startswith('v') else tag
    remote = version_key(version)
    if remote[3] != 1:
        raise UpdateError('invalid_release')
    if remote <= version_key(installed):
        return version, None
    name = installer_name(version, platform, arch)
    assets = release.get('assets')
    if not isinstance(assets, list) or len(assets) > 100:
        raise UpdateError('invalid_release')
    matches = [row for row in assets if isinstance(row, dict) and row.get('name') == name]
    if not matches:
        return version, None
    if len(matches) != 1:
        raise UpdateError('invalid_release')
    asset = matches[0]
    size, digest = asset.get('size'), asset.get('digest')
    expected = 'https://github.com/' + REPOSITORY + '/releases/download/' + urllib.parse.quote(tag, safe='') + '/' + urllib.parse.quote(name, safe='')
    if (asset.get('state') != 'uploaded' or asset.get('browser_download_url') != expected
            or type(size) is not int or not 0 < size <= MAX_PACKAGE
            or not isinstance(digest, str) or re.fullmatch(r'sha256:[0-9a-f]{64}', digest) is None):
        raise UpdateError('invalid_release')
    return version, {'version': version, 'name': name, 'url': expected, 'size': size, 'sha256': digest[7:]}


class UpdateManager:
    def __init__(self, root, installed, platform, arch=None, fetcher=fetch_release, opener=open_url, resources=None, applier=None):
        self.root, self.installed, self.platform = Path(root), installed, platform
        self.arch = arch or architecture()
        self.fetcher, self.opener = fetcher, opener
        self.resources = Path(resources or root)
        self.applier = applier
        self.envelope = None
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='router-update')
        self.generation = 0
        self.stop = threading.Event()
        self.future = None
        self.package = None
        self.next_check = 0
        self.state = {'status': 'idle', 'installedVersion': installed, 'latestVersion': None, 'checkedAt': None,
                      'progress': 0, 'error': None, 'canDownload': False, 'canInstall': False,
                      'publisherVerified': False, 'canUpdate': False, 'shutdownForUpdate': False}
        try:
            receipt = self.root / 'state/updates/result.json'
            if receipt.stat().st_size <= 2048:
                result = json.loads(receipt.read_bytes())
                if (result.get('status') in ('completed', 'rolled_back', 'failed')
                        and type(result.get('at')) in (int, float) and 0 <= time.time() - result['at'] < 86400
                        and (result['status'] != 'completed' or result.get('version') == installed)):
                    self.state['status'] = result['status']
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def maybe_check(self, enabled):
        """Opt-in daily checks; never run a network request on the polling thread."""
        with self.lock:
            if (enabled is True and time.monotonic() >= self.next_check
                    and (self.future is None or self.future.done())
                    and self.state['status'] not in ('available', 'downloaded', 'preparing_install', 'installing')):
                self.start('check')

    def _set(self, generation, **fields):
        with self.lock:
            if generation == self.generation and not self.stop.is_set():
                self.state.update(fields)
                return True
        return False

    def start(self, operation):
        if operation not in ('check', 'download', 'install', 'cancel'):
            raise ValueError('Acción de actualización no válida.')
        with self.lock:
            if self.state['shutdownForUpdate']:
                return 'La instalación ya está preparada; espera a que termine.'
            if operation == 'cancel':
                self.stop.set(); self.generation += 1
                self.state.update(status='cancelled', progress=0, error=None, canInstall=False, canDownload=self.package is not None)
                return 'Operación de actualización cancelada.'
            if self.future is not None and not self.future.done():
                return 'Espera a que termine la operación actual.'
            if operation in ('download', 'install') and self.package is None:
                raise ValueError('Comprueba primero las actualizaciones disponibles.')
            if operation == 'install' and not (self.state['canUpdate'] and self.applier):
                raise ValueError('La instalación automática aún no está disponible para esta entrega.')
            self.stop = threading.Event(); self.generation += 1
            generation = self.generation
            self.state.update(status='checking' if operation == 'check' else 'downloading', error=None, progress=0, canDownload=False)
            if operation == 'check':
                self.package = None; self.envelope = None
                self.next_check = time.monotonic() + 86400
                self.state.update(latestVersion=None, checkedAt=None, publisherVerified=False, canUpdate=False, canInstall=False)
            package = dict(self.package) if self.package else None
            self.future = self.executor.submit(self._work, operation, generation, self.stop, package)
            return 'Comprobando actualizaciones…' if operation == 'check' else 'Descargando actualización…'

    def _work(self, operation, generation, stop, package):
        try:
            if operation == 'check':
                release = self.fetcher()
                version, selected = candidate(release, self.installed, self.platform, self.arch)
                envelope = self._authenticate(release, selected) if selected else None
                with self.lock:
                    if generation != self.generation or stop.is_set():
                        return
                    self.package = selected
                    self.envelope = envelope
                    newer = version_key(version) > version_key(self.installed)
                    self.state.update(status='available' if newer and selected else 'package_unavailable' if newer else 'up_to_date',
                                      latestVersion=version, checkedAt=time.time(), canDownload=selected is not None, error=None,
                                      publisherVerified=envelope is not None,
                                      canUpdate=envelope is not None and self.applier is not None)
            else:
                path = self._download(package, generation, stop)
                if operation == 'install' and path and not stop.is_set():
                    from codex_model_router.update_trust import verify, load_keys
                    verify(self.envelope, load_keys(self.resources), package, self.platform, self.arch)
                    self._set(generation, status='preparing_install')
                    # The installed helper re-verifies signature and bytes before apply.
                    handed_off = self.applier.prepare(path, package, self.envelope, stop)
                    if handed_off:
                        self._set(generation, status='installing', canInstall=False, canUpdate=False,
                                  shutdownForUpdate=True)
        except Exception as error:
            from codex_model_router.update_trust import TrustError
            self._set(generation, status='error', error=error.code if isinstance(error, (UpdateError, TrustError)) else 'network_error', canDownload=False, canInstall=False)

    def _authenticate(self, release, package):
        from codex_model_router.update_trust import load_keys, verify, MANIFEST_NAME, MAX_ENVELOPE
        keys = load_keys(self.resources)
        if not keys:
            return None
        matches = [a for a in release['assets'] if isinstance(a, dict) and a.get('name') == MANIFEST_NAME]
        expected = 'https://github.com/' + REPOSITORY + '/releases/download/' + urllib.parse.quote(release['tag_name'], safe='') + '/' + MANIFEST_NAME
        if (len(matches) != 1 or matches[0].get('browser_download_url') != expected
                or matches[0].get('state') != 'uploaded' or type(matches[0].get('size')) is not int
                or not 0 < matches[0]['size'] <= MAX_ENVELOPE):
            raise UpdateError('missing_signature')
        with self.opener(expected) as response:
            raw = response.read(MAX_ENVELOPE + 1)
        if len(raw) != matches[0]['size']:
            raise UpdateError('invalid_signature')
        verify(raw, keys, package, self.platform, self.arch)
        return raw

    def _download(self, package, generation, stop):
        directory = self.root / 'state' / 'updates'
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.download-', dir=directory)
        received, digest = 0, hashlib.sha256()
        began = time.monotonic()
        try:
            with os.fdopen(descriptor, 'wb') as target, self.opener(package['url']) as response:
                length = response.headers.get('Content-Length')
                if length is not None and (not length.isdigit() or int(length) != package['size']):
                    raise UpdateError('invalid_size')
                while True:
                    if stop.is_set():
                        return
                    if time.monotonic() - began > DOWNLOAD_SECONDS:
                        raise UpdateError('network_error')
                    data = response.read(65536)
                    if not data:
                        break
                    received += len(data)
                    if received > package['size']:
                        raise UpdateError('invalid_size')
                    target.write(data); digest.update(data)
                    self._set(generation, progress=int(100 * received / package['size']))
                target.flush(); os.fsync(target.fileno())
            if received != package['size'] or digest.hexdigest() != package['sha256']:
                raise UpdateError('integrity_error')
            with self.lock:
                if generation != self.generation or stop.is_set():
                    return
                destination = directory / package['name']
                os.replace(temporary, destination)
                # Receipt documents integrity only, never publisher authenticity.
                atomic_json(directory / 'staged.json', {key: package[key] for key in ('version', 'name', 'size', 'sha256')})
                self.state.update(status='downloaded', progress=100, canDownload=False, canInstall=False)
                return destination
        finally:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass

    def close(self):
        self.stop.set()
        self.executor.shutdown(wait=False, cancel_futures=True)
