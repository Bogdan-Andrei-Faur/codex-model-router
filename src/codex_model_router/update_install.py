"""Installed Mac update handoff and recoverable application replacement.

Only a user-writable packaged app is eligible. Downloaded PKG scripts are never
run: the authenticated, script-free app payload replaces the owned app. Mutable
user data is not copied, deleted or migrated by an update. Windows and Ubuntu
remain explicitly disabled until their native transaction adapters are tested.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid

from codex_model_router.storage.state_store import atomic_json, file_lock
from codex_model_router.update_trust import load_keys, verify, TrustError

APP_NAME = 'Codex Model Router.app'
APP_ID = 'local.codex-model-router.application'


def clean_environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PERSONAL_CODEX_', '_PYI_', '_MEIPASS', 'DYLD_'))
           and k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'CODEX_CLI_PATH')}
    # New frozen processes must initialize from their own (possibly new) bundle.
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return env


def app_info(app):
    if app.is_symlink() or (app.name != APP_NAME and not re.fullmatch(r'\.router-(?:previous|new)-[0-9a-f]{32}\.app', app.name)):
        raise TrustError('invalid_installation')
    try:
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
        if (info.get('CFBundleIdentifier') != APP_ID or info.get('CFBundleExecutable') != 'codex-monitor-mac'
                or info.get('RouterPackaged') is not True):
            raise ValueError()
        return info
    except (OSError, ValueError, TypeError):
        raise TrustError('invalid_installation') from None


def validate_tree(app):
    base = app.resolve()
    total = 0
    for path in app.rglob('*'):
        info = path.lstat()
        if path.is_symlink():
            if base not in path.resolve().parents:
                raise TrustError('invalid_installation')
        elif stat.S_ISREG(info.st_mode):
            total += info.st_size
            if info.st_mode & (stat.S_ISUID | stat.S_ISGID) or total > 2 * 1024 ** 3:
                raise TrustError('invalid_installation')
        elif not stat.S_ISDIR(info.st_mode):
            raise TrustError('invalid_installation')


def copy_verified(source, destination, package):
    if source.is_symlink():
        raise TrustError('integrity_error')
    digest = hashlib.sha256(); size = 0
    descriptor = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as incoming, destination.open('xb') as outgoing:
        before = os.fstat(incoming.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise TrustError('integrity_error')
        for chunk in iter(lambda: incoming.read(1024 * 1024), b''):
            size += len(chunk)
            if size > package['size']:
                raise TrustError('integrity_error')
            outgoing.write(chunk); digest.update(chunk)
        outgoing.flush(); os.fsync(outgoing.fileno())
    if size != package['size'] or digest.hexdigest() != package['sha256']:
        raise TrustError('integrity_error')


def extract_app(package_path, folder, version):
    subprocess.run(['/usr/sbin/pkgutil', '--expand-full', str(package_path), str(folder)],
                   check=True, capture_output=True, timeout=120)
    if any(p.name == 'Scripts' for p in folder.rglob('*')):
        raise TrustError('invalid_installation')
    apps = list(folder.glob('**/Payload/Applications/' + APP_NAME))
    if len(apps) != 1 or app_info(apps[0]).get('CFBundleShortVersionString') != version:
        raise TrustError('invalid_installation')
    validate_tree(apps[0])
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(apps[0])],
                   check=True, capture_output=True, timeout=30)
    return apps[0]


class MacApplier:
    def __init__(self, root, resources):
        self.root, self.resources = Path(root).resolve(), Path(resources).resolve()
        self.app = self.resources.parent.parent

    def prepare(self, package_path, package, envelope, stop):
        from codex_model_router.platforms.installation_migration import reject_active, MigrationError
        from codex_model_router.updates import architecture, version_key
        old = app_info(self.app)
        if version_key(package['version']) <= version_key(old['CFBundleShortVersionString']):
            raise TrustError('invalid_installation')
        if self.app in self.root.parents or self.root == self.app:
            raise TrustError('invalid_installation')
        if not os.access(self.app.parent, os.W_OK) or not os.access(self.app, os.W_OK):
            raise TrustError('installation_read_only')
        try:
            reject_active(self.root / 'state')
        except MigrationError:
            raise TrustError('active_bridge') from None
        verify(envelope, load_keys(self.resources), package, 'macos', architecture())
        token = uuid.uuid4().hex
        job = self.root / 'state/updates/jobs' / token
        job.mkdir(parents=True, mode=0o700)
        handed_off = False
        try:
            private_package = job / package['name']
            copy_verified(Path(package_path), private_package, package)
            new_app = extract_app(private_package, job / 'expanded', package['version'])
            if stop.is_set():
                return False
            # This installed (old) runtime is copied before closing the monitor,
            # so replacing the live bundle cannot remove the helper's libraries.
            worker = job / APP_NAME
            shutil.copytree(self.app, worker, symlinks=True)
            operation = {'schema': 1, 'token': token, 'app': str(self.app),
                         'oldVersion': old['CFBundleShortVersionString'], 'oldBuild': old.get('RouterBuildId'),
                         'package': package, 'phase': 'prepared'}
            (job / 'signature.json').write_bytes(envelope)
            atomic_json(job / 'operation.json', operation)
            if stop.is_set():
                return False
            from codex_model_router.platforms.application_layout import installed_path
            runtime = installed_path(worker / 'Contents/Resources', 'runtime')
            arguments = [str(runtime), '--data-root', str(self.root), 'update-helper', token]
            # A user LaunchAgent retries an interrupted commit at the next login.
            # It is removed after a terminal receipt; no daemon/root privilege.
            agent = recovery_agent(token)
            agent.parent.mkdir(parents=True, exist_ok=True)
            with agent.open('xb') as stream:
                stream.write(plistlib.dumps({'Label': 'local.codex-model-router.update.' + token,
                    'ProgramArguments': arguments, 'RunAtLoad': True, 'LimitLoadToSessionType': 'Aqua'}))
                stream.flush(); os.fsync(stream.fileno())
            agent.chmod(0o600)
            child = subprocess.Popen(arguments,
                             env=clean_environment(), stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            deadline = time.monotonic() + 120
            while child.poll() is None and time.monotonic() < deadline and not stop.is_set():
                if (job / 'ready-to-close').is_file():
                    handed_off = True
                    return True
                time.sleep(.1)
            (job / 'cancel').touch()
            child.wait(timeout=15)
            raise TrustError('invalid_installation')
        finally:
            if not handed_off:
                if 'child' not in locals() or child.poll() is not None:
                    recovery_agent(token).unlink(missing_ok=True)
                    shutil.rmtree(job)


def installed_applier(root, resources, platform):
    from codex_model_router.platforms.application_layout import manifest
    if platform != 'macos' or sys.platform != 'darwin':
        return None
    try:
        value = manifest(resources)
        if not value or value['layout'] != 'macos-bundle-v1':
            return None
        app_info(Path(resources).resolve().parent.parent)
        return MacApplier(root, resources)
    except (ValueError, OSError):
        return None


def recovery_agent(token):
    return Path.home() / 'Library/LaunchAgents' / ('local.codex-model-router.update.' + token + '.plist')


def recover_interrupted(app, staged, previous, expected_version, old_version):
    """Restore only this job's identified old bundle, never a foreign app."""
    if not previous.exists():
        if app_info(app).get('CFBundleShortVersionString') != old_version:
            raise TrustError('invalid_installation')
        return
    if app_info(previous).get('CFBundleShortVersionString') != old_version:
        raise TrustError('invalid_installation')
    if app.exists():
        if app_info(app).get('CFBundleShortVersionString') != expected_version or staged.exists():
            raise TrustError('invalid_installation')
        os.rename(app, staged)
    os.rename(previous, app)


def replace_and_confirm(app, staged, previous, launch, confirm, record):
    """Recoverable two-rename commit, shared with fault-injection tests.

    All three paths are siblings; never delete a failed candidate or last-good app.
    Before the first rename the old installation is untouched. A failure between
    renames is repaired, as is failure after the new process starts.
    """
    if previous.exists() or app.parent != staged.parent or app.parent != previous.parent:
        raise TrustError('invalid_installation')
    record('committing')
    os.rename(app, previous)
    child = None
    try:
        os.rename(staged, app)
        record('confirming')
        child = launch(app)
        if not confirm(child):
            raise TrustError('launch_failed')
        record('completed')
        return 'completed'
    except Exception:
        # Terminate only the exact monitor child this helper launched. Desktop
        # and pre-existing owner processes are never signalled.
        if child is not None and child.poll() is None:
            child.terminate(); child.wait(timeout=10)
        if app.exists():
            os.rename(app, staged)
        os.rename(previous, app)
        record('rolled_back')
        launch(app)
        return 'rolled_back'


def run_helper(root, resources, token):
    from codex_model_router.updates import architecture, version_key
    from codex_model_router.platforms.installation_migration import reject_active
    root, resources = Path(root).resolve(), Path(resources).resolve()
    if sys.platform != 'darwin' or re.fullmatch('[0-9a-f]{32}', token) is None:
        raise TrustError('invalid_installation')
    job = root / 'state/updates/jobs' / token
    # A copied installed runtime is the sole entry, not a downloaded helper.
    if resources != job / APP_NAME / 'Contents/Resources':
        raise TrustError('invalid_installation')
    operation = json.loads((job / 'operation.json').read_text())
    if operation.get('schema') != 1 or operation.get('token') != token:
        raise TrustError('invalid_installation')
    if operation.get('phase') in ('completed', 'rolled_back', 'failed', 'cancelled'):
        # A crash after recording success but before unlinking the login job must
        # never repeat the replacement or leave a permanently failing agent.
        recovery_agent(token).unlink(missing_ok=True)
        return
    if operation.get('phase') not in ('prepared', 'committing', 'confirming'):
        raise TrustError('invalid_installation')
    app = Path(operation['app'])
    staged = app.parent / ('.router-new-' + token + '.app')
    previous = app.parent / ('.router-previous-' + token + '.app')
    recovering = operation['phase'] in ('committing', 'confirming')
    old = app_info(previous if recovering and previous.exists() else app)
    if (not app.is_absolute() or app.resolve() != app or app in root.parents
            or old.get('RouterBuildId') != operation['oldBuild']
            or old.get('CFBundleShortVersionString') != operation['oldVersion']):
        raise TrustError('invalid_installation')
    package = operation['package']
    if version_key(package['version']) <= version_key(operation['oldVersion']):
        raise TrustError('invalid_installation')
    verify((job / 'signature.json').read_bytes(), load_keys(resources), package, 'macos', architecture())
    # Re-read the authenticated archive, rather than trusting extracted files or
    # a mutable staged.json receipt from the downloader.
    def record(phase):
        operation['phase'] = phase
        atomic_json(job / 'operation.json', operation)
        atomic_json(root / 'state/updates/result.json', {'schema': 1, 'status': phase,
                    'version': package['version'], 'at': time.time()})
    def launch(target):
        child = subprocess.Popen([str(target / 'Contents/MacOS/codex-monitor-mac'), str(root), '--update-ready=' + token],
                                env=clean_environment(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        operation['monitorPid'] = child.pid
        try:
            atomic_json(job / 'operation.json', operation)
        except OSError:
            pass
        return child
    def confirm(child):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline and child.poll() is None:
            if (job / 'ready').is_file():
                return True
            time.sleep(.2)
        return False
    try:
        with file_lock(app.parent / '.codex-router-update.lock', timeout=.1):
            if recovering:
                with file_lock(root / 'state/monitor-mac.lock', timeout=.1):
                    reject_active(root / 'state')
                    recover_interrupted(app, staged, previous, package['version'], operation['oldVersion'])
                    record('rolled_back')
                launch(app)
                recovery_agent(token).unlink(missing_ok=True)
                return
            checked = job / ('checked-' + package['name'])
            copy_verified(job / package['name'], checked, package)
            candidate = extract_app(checked, job / 'rechecked', package['version'])
            shutil.copytree(candidate, staged, symlinks=True)
            (job / 'ready-to-close').touch()
            deadline = time.monotonic() + 120
            while True:
                if (job / 'cancel').exists() or time.monotonic() > deadline:
                    record('cancelled'); recovery_agent(token).unlink(missing_ok=True); return
                lease = file_lock(root / 'state/monitor-mac.lock', timeout=.1)
                try:
                    lease.__enter__(); break
                except TimeoutError:
                    time.sleep(.1)
            released = False
            def launch_after_unlock(target):
                nonlocal released
                if not released:
                    lease.__exit__(None, None, None); released = True
                return launch(target)
            try:
                reject_active(root / 'state')
                replace_and_confirm(app, staged, previous, launch_after_unlock, confirm, record)
            finally:
                if not released:
                    lease.__exit__(None, None, None)
            recovery_agent(token).unlink(missing_ok=True)
    except Exception:
        # Keep interrupted-commit provenance and its recovery LaunchAgent. A
        # timeout/unknown competing process must never overwrite an app.
        if operation['phase'] not in ('committing', 'confirming'):
            record('failed')
            recovery_agent(token).unlink(missing_ok=True)
            try:
                with file_lock(root / 'state/monitor-mac.lock', timeout=.1):
                    unchanged = app_info(app).get('CFBundleShortVersionString') == operation['oldVersion']
                if unchanged:
                    launch(app)
            except (ValueError, OSError, TimeoutError):
                pass
        raise
