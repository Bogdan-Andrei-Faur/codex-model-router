"""Guarded offline import into a new data root; source data is never overwritten.

This imports known product data, not a repository/build tree. It does not transfer
Desktop registration, activate a bridge, close apps or decrypt any credentials.
Coordination lock files may be created in the source state directory.
"""
from contextlib import ExitStack
import json
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from application_layout import credential_namespace
from state_store import atomic_json, file_lock

FILES = ('history.jsonl', 'history.recovered.jsonl', 'prompts.jsonl', 'jev-health.json',
         'keychain-revision.json', 'credential-namespace.json', 'monitor-ui-mac.json',
         'monitor-ui-linux.json', 'monitor-ui-windows.json', 'monitor-ui.json', 'jev-typesafe.secret', 'jev-vercel.secret')
DIRECTORIES = ('task-modes', 'workloads')


def linked(path):
    """Reject Windows junctions/reparse points as well as POSIX symlinks."""
    path=Path(path)
    if path.is_symlink():return True
    try:return bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:return False


class MigrationError(ValueError):
    """Fixed, user-safe diagnostics: never embed configuration or secret values."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def windows_process_started_at(pid):
    """Read creation time from the process handle; unknown ownership stays blocked."""
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None
        return ((created.dwHighDateTime << 32) | created.dwLowDateTime) / 10000000 - 11644473600
    finally:
        kernel.CloseHandle(handle)


def snapshot_pid_reused(record):
    """An expired heartbeat alone cannot dismiss a live, possibly stalled bridge."""
    heartbeat = record.get('heartbeat')
    if type(heartbeat) not in (int, float) or not math.isfinite(heartbeat) or heartbeat <= 0:
        return False
    started = windows_process_started_at(record['pid'])
    # A new process cannot have written a snapshot from before it existed.
    # Keep a one-second margin for timestamp precision; uncertainty stays blocked.
    return started is not None and started > heartbeat + 1


def reject_active(state):
    if os.name=='nt':
        # WPF owns a named mutex, rather than the Unix monitor lock files.
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenMutexW.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_wchar_p]
        kernel.OpenMutexW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        name='Local\\CodexRouterMonitor-'+hashlib.sha256(str(Path(state).parent.resolve()).upper().encode('utf-8')).hexdigest().upper()
        handle=kernel.OpenMutexW(0x100000,False,name)
        if handle:
            kernel.CloseHandle(handle)
            raise MigrationError('busy_source','El monitor anterior sigue abierto. Ciérralo antes de importar; tus datos se conservan.')
        if ctypes.get_last_error() not in (0,2):
            raise MigrationError('busy_source','No se pudo comprobar el monitor anterior. Se han conservado los datos.')
    from monitor_state import alive
    for path in state.glob('status-*.json'):
        if linked(path): raise ValueError('La instalación contiene enlaces no compatibles.')
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            raise MigrationError('unreadable_status', 'No se puede comprobar el estado de la instalación anterior.') from None
        if not isinstance(record,dict) or type(record.get('pid')) is not int or record['pid'] <= 0:
            raise MigrationError('unreadable_status', 'No se puede comprobar el estado de la instalación anterior.')
        events = record.get('events')
        # A terminated bridge leaves its snapshot behind. Its PID can later be
        # reused by Chrome or any other app; that is not an active router session.
        if isinstance(events, list) and events and isinstance(events[-1], dict) and events[-1].get('event') == 'bridge_stopped':
            continue
        if alive(record['pid']) and not snapshot_pid_reused(record):
            raise MigrationError('active_bridge', 'Codex todavía está usando la instalación anterior. Termina las tareas y cierra Codex antes de importar.')


def copy_stable(source, destination):
    if linked(source) or not source.is_file():
        raise ValueError('La instalación contiene enlaces o archivos no compatibles.')
    before = source.stat()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with source.open('rb') as incoming, destination.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1024*1024)
        outgoing.flush(); os.fsync(outgoing.fileno())
    if os.name != 'nt': destination.chmod(0o600)
    after = source.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Los datos cambiaron durante la importación. La instalación original se conserva.')


def import_legacy(source, destination, platform=None, record_source=False):
    source = Path(source).expanduser()
    destination = Path(destination).expanduser()
    if linked(source) or linked(destination): raise ValueError('La ruta de instalación no es válida.')
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('La instalación y el destino deben ser independientes.')
    if destination.exists(): raise MigrationError('occupied_destination', 'La instalación nueva ya contiene datos. Se han conservado; no se puede importar encima.')
    config_path=source/'config.local.json'; state=source/'state'
    if linked(config_path) or linked(state): raise ValueError('La instalación contiene enlaces no compatibles.')
    try:
        config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        raise MigrationError('missing_config', 'La carpeta seleccionada no contiene config.local.json. Selecciona la carpeta de la instalación anterior, no Documents ni state.') from None
    except (json.JSONDecodeError, UnicodeError):
        raise MigrationError('invalid_config', 'config.local.json no contiene una configuración JSON válida. La instalación original se conserva.') from None
    target_platform = platform or sys.platform
    # The original Windows source installer predates the platform field.
    # Mac/Linux source installers always wrote it; never infer their identity.
    legacy_windows = isinstance(config, dict) and 'platform' not in config and target_platform == 'win32'
    if not isinstance(config,dict) or (config.get('platform') != target_platform and not legacy_windows):
        raise MigrationError('foreign_platform', 'La configuración seleccionada pertenece a otro sistema. Selecciona la instalación de este ordenador.')
    reject_active(state)
    destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.router-import-',dir=destination.parent))
    committed=False
    try:
        with ExitStack() as locks:
            locks.enter_context(file_lock(destination.parent/'.router-import.lock'))
            for name in ('config.lock','history.lock','prompts.lock','workloads.lock','monitor-mac.lock','monitor-linux.lock'):
                locks.enter_context(file_lock(state/name,timeout=.1))
            reject_active(state)
            copy_stable(config_path,temporary/'config.local.json')
            if legacy_windows:
                copied_config=json.loads((temporary/'config.local.json').read_text(encoding='utf-8-sig'))
                if copied_config != config:
                    raise MigrationError('busy_source', 'La configuración cambió. Vuelve a importar cuando el monitor anterior esté cerrado.')
                atomic_json(temporary/'config.local.json', dict(copied_config, platform='win32'))
            count=1
            for name in FILES:
                path=state/name
                if path.exists() or linked(path): copy_stable(path,temporary/'state'/name);count+=1
            for name in DIRECTORIES:
                directory=state/name
                if linked(directory): raise ValueError('La instalación contiene enlaces no compatibles.')
                if not directory.exists():continue
                for path in directory.iterdir():
                    if linked(path) or not re.fullmatch(r'[0-9a-f]{64}\.json',path.name):
                        raise ValueError('La instalación contiene datos de tareas no compatibles.')
                    copy_stable(path,temporary/'state'/name/path.name);count+=1
            # Retain Keychain/Secret Service identity without ever retrieving keys.
            atomic_json(temporary/'state/credential-namespace.json',{'namespace':credential_namespace(source)})
            atomic_json(temporary/'state/migration.json',{'schema':1,'filesImported':count,'integrationPending':True,'sourcePreserved':True})
            if record_source:
                atomic_json(temporary/'state/legacy-installation.json',{'schema':1,'root':str(source)})
            reject_active(state)
            if destination.exists():raise ValueError('El destino cambió; no se han sustituido sus datos.')
            os.rename(temporary,destination);committed=True
        return {'imported':True,'filesImported':count,'integrationPending':True,'sourcePreserved':True}
    except TimeoutError:
        raise MigrationError('busy_source', 'El monitor anterior o una escritura de datos sigue activo. Cierra el monitor anterior y vuelve a importar.') from None
    finally:
        if not committed:shutil.rmtree(temporary)
