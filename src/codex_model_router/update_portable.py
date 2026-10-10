"""Managed Windows setup and per-user Linux runtime transactions.

No privileged commands, process-wide termination, or mutable user-data migration.
The installed old runtime owns recovery, including after a session restart.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

from codex_model_router.storage.state_store import atomic_json, file_lock, private_directory
from codex_model_router.platforms.application_layout import manifest, installed_path
from codex_model_router.update_install import clean_environment, copy_verified, validate_tree
from codex_model_router.update_trust import TrustError, load_keys, verify

TOKEN = re.compile(r'[0-9a-f]{32}')
TERMINAL = ('completed', 'rolled_back', 'failed', 'cancelled')


def read(path):
    if path.stat().st_size > 65536:
        raise TrustError('invalid_installation')
    return json.loads(path.read_bytes())


def reject_active(root):
    from codex_model_router.platforms.installation_migration import reject_active as check, MigrationError
    try:
        check(root / 'state')
    except MigrationError:
        raise TrustError('active_bridge') from None


def extract_linux(archive, destination):
    """Inspect all tar entries before extraction. Never execute DEBIAN scripts."""
    destination.mkdir()
    with tempfile.TemporaryFile() as stream:
        subprocess.run(['/usr/bin/dpkg-deb', '--fsys-tarfile', str(archive)], stdout=stream,
                       stderr=subprocess.DEVNULL, check=True, timeout=120)
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode='r:') as payload:
            entries = payload.getmembers()
            total = 0
            for item in entries:
                path = Path(item.name)
                total += item.size
                if (path.is_absolute() or '..' in path.parts or len(entries) > 50000
                        or total > 2 * 1024**3 or item.mode & 0o6000
                        or not (item.isfile() or item.isdir() or item.issym())):
                    raise TrustError('invalid_installation')
                if item.issym():
                    # Only the system launcher's known relative link is needed;
                    # it is outside the extracted application and isn't installed.
                    if item.name.lstrip('./') != 'usr/bin/codex-model-router' or item.linkname != '../lib/codex-model-router/bin/codex-monitor-linux':
                        raise TrustError('invalid_installation')
            prefix = 'usr/lib/codex-model-router/'
            for item in entries:
                name = item.name.removeprefix('./')
                if not name.startswith(prefix):
                    continue
                target = destination / name[len(prefix):]
                if item.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif item.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with payload.extractfile(item) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(item.mode & 0o755)
    validate_tree(destination)
    resources = destination / 'Resources'
    if manifest(resources).get('layout') != 'linux-deb-v1':
        raise TrustError('invalid_installation')
    return resources


def selection_path(root):
    return root / 'state/updates/linux-active.json'


def linux_selected(root, baseline):
    """Select only committed owned runtime paths; a newer apt baseline wins."""
    from codex_model_router.updates import version_key
    pointer = selection_path(root)
    if not pointer.exists():
        return baseline
    value = read(pointer)
    token = value.get('token', '')
    if not isinstance(token, str) or not TOKEN.fullmatch(token):
        raise TrustError('invalid_installation')
    candidate = root / 'state/updates/jobs' / token / 'candidate/Resources'
    if candidate.is_symlink() or candidate.resolve() != candidate:
        raise TrustError('invalid_installation')
    if manifest(candidate).get('layout') != 'linux-deb-v1':
        raise TrustError('invalid_installation')
    if version_key((candidate/'VERSION').read_text().strip()) <= version_key((baseline/'VERSION').read_text().strip()):
        return baseline
    return candidate


def windows_install_command(archive, application):
    return [str(archive), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART',
            '/RESTARTEXITCODE=3010', '/NOCLOSEAPPLICATIONS', '/NORESTARTAPPLICATIONS',
            '/DIR=' + str(application)]


def windows_installer_running():
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenMutexW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.OpenMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenMutexW(0x00100000, False, 'Local\\CodexModelRouterSetup')
    if handle:
        kernel.CloseHandle(handle)
        return True
    # Missing object is the sole safe negative; access denial is not absence.
    return ctypes.get_last_error() != 2


def recoverable_selection(current, operation):
    if current == operation['previous']:
        return True
    if not isinstance(current, dict):
        return False
    if operation['platform'] == 'linux':
        return current == {'token': operation['token']}
    version = current.get('versionDirectory', '')
    return isinstance(version, str) and re.fullmatch(re.escape(operation['package']['version']) + r'-[0-9a-f]{16}', version) is not None


def register_recovery(root, token, command, remove=False):
    name = 'CodexRouterUpdate-' + token
    if sys.platform == 'win32':
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            if remove:
                try: winreg.DeleteValue(key, name)
                except FileNotFoundError: pass
            else:
                # Run values are limited to 260 characters. Dispatch through
                # the stable launcher instead of duplicating the long job path.
                operation = read(root/'state/updates/jobs'/token/'operation.json')
                launcher = Path(operation['application'])/'bin/codex-router.exe'
                default = Path(os.environ['LOCALAPPDATA'])/'codex-model-router'
                args = [str(launcher)]
                if root != default: args += ['--data-root', str(root)]
                args += ['--recover-update', token]
                line = subprocess.list2cmdline(args)
                if len(line.encode('utf-16-le')) // 2 > 260: raise TrustError('recovery_path_too_long')
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, line)
    else:
        # Desktop Entry Exec quoting, not shell quoting. No shell is invoked.
        base = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))
        if not base.is_absolute():
            base = Path.home()/'.config'
        entry = base / 'autostart' / (name + '.desktop')
        if remove:
            entry.unlink(missing_ok=True)
        else:
            entry.parent.mkdir(parents=True, exist_ok=True)
            def quote(arg):
                if any(c in arg for c in '\n\r\0'):
                    raise TrustError('invalid_installation')
                return '"' + arg.replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%') + '"'
            entry.write_text('[Desktop Entry]\nType=Application\nName=Codex Model Router recovery\nExec='
                             + ' '.join(quote(x) for x in command) + '\nTerminal=false\n')
            entry.chmod(0o600)


class PortableApplier:
    def __init__(self, root, resources, platform):
        self.root, self.resources = Path(root).resolve(), Path(resources).resolve()
        self.platform = platform

    def prepare(self, archive, package, envelope, stop):
        from codex_model_router.updates import architecture, version_key
        reject_active(self.root)
        if version_key(package['version']) <= version_key((self.resources/'VERSION').read_text().strip()):
            raise TrustError('invalid_installation')
        verify(envelope, load_keys(self.resources), package, self.platform, architecture())
        token = uuid.uuid4().hex
        job = private_directory(self.root / 'state/updates/jobs' / token)
        handed = False
        command = []
        try:
            copy_verified(archive, job/package['name'], package)
            if stop.is_set(): return False
            # A self-contained old runtime outside the Windows install survives
            # installer locked-file checks. Linux recovery survives apt changes.
            shutil.copytree(self.resources.parent, job/'worker', symlinks=True)
            validate_tree(job/'worker')
            worker = job/'worker/Resources'
            application = self.resources.parent.parent.parent if self.platform == 'windows' else None
            pointer = application/'active.json' if application else selection_path(self.root)
            previous = read(pointer) if pointer.exists() else None
            operation = dict(schema=1, token=token, platform=self.platform, package=package,
                             application=str(application) if application else None,
                             oldResources=str(self.resources), previous=previous, phase='prepared')
            atomic_json(job/'operation.json', operation)
            # UpdateManager passes the original signed JSON bytes. Preserve
            # them exactly; serializing bytes as an object breaks every handoff.
            (job/'signature.json').write_bytes(envelope)
            command = [str(installed_path(worker, 'runtime')), '--data-root', str(self.root), 'update-helper', token]
            register_recovery(self.root, token, command)
            child = subprocess.Popen(command, env=clean_environment(), stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     **({'creationflags': 0x08000000} if sys.platform == 'win32' else {'start_new_session': True}))
            deadline = time.monotonic() + 120
            while child.poll() is None and time.monotonic() < deadline:
                if stop.is_set(): return False
                if (job/'ready-to-close').exists():
                    handed = True
                    return True
                time.sleep(.1)
            raise TrustError(read(job/'operation.json').get('error', 'invalid_installation'))
        finally:
            if not handed:
                (job/'cancel').touch()
                if 'child' not in locals() or child.poll() is not None:
                    register_recovery(self.root, token, command, remove=True)


def native_ready(root, token):
    if token and TOKEN.fullmatch(token):
        job = root/'state/updates/jobs'/token
        if (job/'operation.json').is_file():
            (job/'ready').write_text('ready')


def wait_monitor(root, platform, job):
    """Wait for graceful native shutdown; never terminate the owner's process."""
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if (job/'cancel').exists(): return False
        try:
            with monitor_lease(root, platform): return True
        except TimeoutError: time.sleep(.1)
    return False


def monitor_lease(root, platform):
    # Both hosts hold this same file lease for their complete native lifecycle.
    return file_lock(root/('state/monitor-' + ('windows' if platform == 'windows' else 'linux') + '.lock'), timeout=.1)


def run_helper(root, resources, token):
    root, resources = Path(root).resolve(), Path(resources).resolve()
    if not TOKEN.fullmatch(token): raise TrustError('invalid_installation')
    job = root/'state/updates/jobs'/token
    if resources != job/'worker/Resources': raise TrustError('invalid_installation')
    operation = read(job/'operation.json')
    if operation.get('schema') != 1 or operation.get('token') != token or operation.get('phase') not in ('prepared', 'committing', 'confirming', *TERMINAL):
        raise TrustError('invalid_installation')
    platform = operation['platform']
    if platform != {'win32': 'windows', 'linux': 'linux'}.get(sys.platform):
        raise TrustError('invalid_installation')
    command = [str(installed_path(resources,'runtime')), '--data-root',str(root),'update-helper',token]
    def record(phase):
        operation['phase'] = phase
        atomic_json(job/'operation.json', operation)
        if phase in TERMINAL:
            atomic_json(root/'state/updates/result.json', dict(status=phase, version=operation['package']['version'], at=time.time()))
            register_recovery(root, token, command, remove=True)
    if operation['phase'] in TERMINAL:
        register_recovery(root, token, command, remove=True)
        return
    app = Path(operation['application']) if platform == 'windows' else None
    old = Path(operation['oldResources'])
    if platform == 'windows' and (old.parent.parent.name != 'versions' or old.parent.parent.parent != app):
        raise TrustError('invalid_installation')
    pointer = app/'active.json' if app else selection_path(root)
    def launch(target, ack=False):
        arguments = [str(installed_path(target, 'monitor'))]
        if platform == 'windows': arguments += ['--root', str(root)]
        else: arguments = [str(installed_path(target, 'runtime')), '--data-root',str(root),'monitor']
        if ack: arguments += ['--update-ready='+token]
        return subprocess.Popen(arguments, env=clean_environment(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def restore():
        previous = operation['previous']
        if previous is None: pointer.unlink(missing_ok=True)
        else: atomic_json(pointer, previous)
        record('rolled_back')
    with file_lock(root/'state/updates/transaction.lock', timeout=.1):
        recovering = operation['phase'] in ('committing', 'confirming')
        if recovering:
            # A replay never races a surviving installer/native process.
            with monitor_lease(root, platform):
                reject_active(root)
                if not recoverable_selection(read(pointer) if pointer.exists() else None, operation):
                    raise TrustError('installation_changed')
                if platform == 'windows':
                    if windows_installer_running():
                        raise TrustError('active_bridge')
                    check = subprocess.run([str(app/'bin/codex-router.exe'),'--check-installation',str(app)], timeout=45)
                    if check.returncode: raise TrustError('active_bridge')
                restore()
            launch(old)
            return
        child = None
        try:
            from codex_model_router.updates import architecture
            signature = job/'signature.json'
            if signature.stat().st_size > 65536:
                raise TrustError('invalid_signature')
            verify(signature.read_bytes(), load_keys(resources), operation['package'], platform, architecture())
            checked = job/('verified-' + operation['package']['name'])
            # Replay before commit can leave a verified copy; never trust it.
            checked.unlink(missing_ok=True)
            copy_verified(job/operation['package']['name'], checked, operation['package'])
            if platform == 'linux':
                candidate = job/'candidate'
                if candidate.exists(): shutil.rmtree(candidate)
                target = extract_linux(checked, candidate)
                if manifest(target).get('managedUpdateProtocol') != 1:
                    raise TrustError('invalid_installation')
                if manifest(target).get('runtimeDependencies') != manifest(resources).get('runtimeDependencies'):
                    raise TrustError('baseline_upgrade_required')
                if (target/'VERSION').read_text().strip() != operation['package']['version']:
                    raise TrustError('invalid_installation')
                # Check runtime dependencies without loading the candidate UI.
                subprocess.run([str(installed_path(target,'runtime')), '--data-root',str(root),'identity'],
                               env=clean_environment(), capture_output=True, check=True, timeout=45)
                subprocess.run(['/usr/bin/python3', '-I', '-c',
                                'import cryptography,gi; gi.require_version("Gtk","3.0"); gi.require_version("WebKit2","4.1"); from gi.repository import Gtk,WebKit2'],
                               env=clean_environment(), capture_output=True, check=True, timeout=45)
            (job/'ready-to-close').touch()
            if not wait_monitor(root, platform, job): record('cancelled'); return
            with monitor_lease(root, platform):
                reject_active(root)
                if (job/'cancel').exists(): record('cancelled'); return
                current = read(pointer) if pointer.exists() else None
                if current != operation['previous']:
                    raise TrustError('installation_changed')
                record('committing')
                if platform == 'windows':
                    subprocess.run(windows_install_command(checked, app), env=clean_environment(),
                                   check=True)  # Never kill an installer on an arbitrary timeout.
                    selected = read(pointer)['versionDirectory']
                    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{16}',selected):
                        raise TrustError('invalid_installation')
                    target = app/'versions'/selected/'Resources'
                    if (target/'VERSION').read_text().strip() != operation['package']['version']:
                        raise TrustError('invalid_installation')
                else:
                    atomic_json(pointer, dict(token=token))
                record('confirming')
            (job/'ready').unlink(missing_ok=True)
            child = launch(target, ack=True)
            deadline = time.monotonic()+60
            while time.monotonic()<deadline and child.poll() is None:
                if (job/'ready').exists(): record('completed'); return
                time.sleep(.2)
            raise TrustError('launch_failed')
        except Exception as error:
            operation['error'] = error.code if isinstance(error, TrustError) else 'install_failed'
            if operation['phase'] in ('committing','confirming'):
                # Only the child launched by this helper may be stopped.
                if child and child.poll() is None:
                    child.terminate(); child.wait(timeout=15)
                with monitor_lease(root, platform):
                    reject_active(root)
                    if not recoverable_selection(read(pointer) if pointer.exists() else None, operation):
                        raise TrustError('installation_changed')
                    restore()
                launch(old)
            else:
                record('failed')
                try:
                    with monitor_lease(root, platform): pass
                    if (read(pointer) if pointer.exists() else None) == operation['previous']:
                        launch(old)
                except (OSError, TimeoutError):
                    pass
            raise
