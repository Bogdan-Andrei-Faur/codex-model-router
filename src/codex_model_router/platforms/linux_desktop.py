"""Reversible XDG desktop integration. Never change system launchers or sessions."""
import base64
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

from codex_model_router.platforms.desktop_runtime import DiscoveryError
from codex_model_router.storage.state_store import atomic_json, file_lock


def applications():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications'


def desktop_source(config):
    name = config.get('desktop_entry', 'chatgpt.desktop')
    if Path(name).name != name or not name.endswith('.desktop'):
        raise DiscoveryError('El identificador del acceso de Desktop no es válido.')
    target = applications() / name
    roots = [applications(), *[Path(p) / 'applications' for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]]
    source = next((root / name for root in roots if (root / name).is_file()), None)
    if source is None:
        raise DiscoveryError('No se encuentra el acceso .desktop. Indica desktop_entry en la configuración local.')
    return source, target


def entry_quote(value):
    # Two escape layers: Desktop Entry string, then Exec double-quoted argument.
    value = str(value).replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%')
    if '\n' in value or '\r' in value:
        raise DiscoveryError('La ruta contiene un salto de línea no admitido.')
    return '"' + value + '"'


def wrapped_entry(text, launcher):
    section = None
    output = []
    found = False
    for line in text.splitlines(keepends=True):
        if line.strip().startswith('['):
            section = line.strip()
        if line.startswith('Exec=') and (section == '[Desktop Entry]' or (section or '').startswith('[Desktop Action ')):
            original = line[5:].rstrip('\r\n')
            if not original or 'codex-desktop' in original:
                raise DiscoveryError('El acceso ya usa otro selector o no tiene un comando válido.')
            line = 'Exec=' + entry_quote(launcher) + ' ' + original + '\n'
            found = True
        if section == '[Desktop Entry]' and line.startswith('DBusActivatable='):
            line = 'DBusActivatable=false\n'  # Exec must run rather than bypassing it via D-Bus.
        output.append(line)
    if not found:
        raise DiscoveryError('El acceso de Desktop no contiene Exec.')
    return ''.join(output)


def atomic_text(path, text, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.router-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def registration(root):
    try:
        return json.loads((Path(root) / 'state/desktop-integration.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None


def registered(root):
    record = registration(root)
    if not record or record.get('platform') != 'linux' or record.get('status') != 'registered':
        return False
    target = Path(record['target'])
    return target.is_file() and fingerprint(target.read_bytes()) == record['installed_sha256'] and Path(record['wrapper']).is_file()


def fallback_launcher(root, launcher):
    """A user-owned shim survives apt removal and runs the original Exec argv."""
    path = Path(root) / 'state/launchers/codex-desktop'
    target = shlex.quote(str(launcher))
    content = '#!/bin/sh\n' + 'if [ -x ' + target + ' ]; then\n'
    content += '  export PERSONAL_CODEX_ROUTER_ROOT=' + shlex.quote(str(Path(root).resolve())) + '\n'
    content += '  exec ' + target + ' "$@"\nfi\n'
    content += 'unset CODEX_CLI_PATH PERSONAL_CODEX_ROUTER_CONFIG PERSONAL_CODEX_ROUTER_ROOT PERSONAL_CODEX_ROUTER_CODE_ROOT PERSONAL_CODEX_ROUTER_STATE\nexec "$@"\n'
    atomic_text(path, content, 0o700)
    return path


def legacy_root(root):
    marker = Path(root) / 'state/legacy-installation.json'
    if not marker.exists():
        return None
    value = json.loads(marker.read_text())
    source = Path(value['root']).resolve()
    if value.get('schema') != 1 or source == Path(root).resolve():
        raise DiscoveryError('La referencia de migración no es válida.')
    return source if source.is_dir() else None


def install(root, config, installation, probe, wrapper=None, launcher=None, monitor=None):
    root = Path(root)
    packaged = wrapper is not None
    wrapper = Path(wrapper) if packaged else root / 'dist/codex-router'
    launcher = Path(launcher) if packaged else root / 'dist/codex-desktop'
    state = root / 'state'
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with ExitStack() as locks:
        locks.enter_context(file_lock(state / 'desktop-integration.lock'))
        record = registration(root)
        if record:
            if record.get('platform') != 'linux' or record.get('wrapper') != str(wrapper):
                raise DiscoveryError('Existe una conexión de otra instalación; no se ha sustituido.')
            if registered(root):
                legacy = legacy_root(root) if packaged and monitor is not None else None
                if legacy:
                    from codex_model_router.platforms.linux_legacy_handoff import redirect_launchers
                    redirect_launchers(root, legacy, wrapper, monitor, installation.backend, launcher)
                return {'registered': True, 'message': 'Conexión ya instalada. Se aplica al siguiente arranque de Desktop.'}
            if record.get('status') == 'registered':
                raise DiscoveryError('El acceso cambió después de instalar el selector. Se ha conservado.')
        check = subprocess.run([str(wrapper), '--version'], capture_output=True, timeout=45)
        if check.returncode or not check.stdout.startswith(b'codex-cli '):
            raise DiscoveryError('El puente no supera la prueba de arranque.')
        checks = probe(wrapper)
        source, target = desktop_source(config)
        original = source.read_bytes()
        previous = target.read_bytes() if target.exists() else None
        previous_mode = target.stat().st_mode & 0o777 if target.exists() else None
        rollback, rollback_mode = previous, previous_mode
        legacy = legacy_root(root) if packaged else None
        if legacy:
            locks.enter_context(file_lock(legacy / 'state/desktop-integration.lock'))
            old = registration(legacy)
            if old and old.get('status') == 'registered':
                from codex_model_router.platforms.installation_migration import reject_active
                reject_active(legacy / 'state')
                if Path(old['target']) != target:
                    raise DiscoveryError('La conexión anterior ha cambiado. Se ha conservado.')
                legacy_previous = base64.b64decode(old['previous']) if old['previous'] is not None else None
                if registered(legacy):
                    previous = legacy_previous
                    previous_mode = old.get('previous_mode')
                    source = Path(old['source'])
                    original = previous if previous is not None else source.read_bytes()
                elif previous != legacy_previous:
                    # After disconnecting the migrated package, the true original
                    # is restored. Permit reconnect without reviving the old shim.
                    raise DiscoveryError('La conexión anterior ha cambiado. Se ha conservado.')
        if packaged:
            launcher = fallback_launcher(root, launcher)
        desired = wrapped_entry(original.decode('utf-8'), launcher).encode('utf-8')
        record = {'schema': 1, 'platform': 'linux', 'status': 'preparing', 'wrapper': str(wrapper),
                  'target': str(target), 'previous': base64.b64encode(previous).decode('ascii') if previous is not None else None,
                  'previous_mode': previous_mode,
                  'source': str(source), 'installed_sha256': fingerprint(desired),
                  'installed_at': time.time(), 'desktop_version': installation.version, 'protocol_checks': checks}
        # Persist the recovery information before touching the user's shortcut.
        atomic_json(state / 'desktop-integration.json', record)
        try:
            atomic_text(target, desired.decode('utf-8'), 0o644)
            record['status'] = 'registered'
            atomic_json(state / 'desktop-integration.json', record)
        except Exception:
            if target.exists() and fingerprint(target.read_bytes()) == record['installed_sha256']:
                if rollback is None:
                    target.unlink()
                else:
                    atomic_text(target, rollback.decode('utf-8'), rollback_mode or 0o644)
            raise
    if packaged and monitor is not None and legacy:
        from codex_model_router.platforms.linux_legacy_handoff import redirect_launchers
        redirect_launchers(root, legacy, wrapper, monitor, installation.backend, launcher)
    return {'registered': True, 'desktop_version': installation.version,
            'message': 'Conexión instalada. Cierra Desktop cuando terminen tus tareas y ábrelo desde su acceso habitual. La sesión actual no cambia.'}


def restore_previous(record):
    target = Path(record['target'])
    if record['previous'] is None:
        target.unlink(missing_ok=True)
    else:
        atomic_text(target, base64.b64decode(record['previous']).decode('utf-8'), record.get('previous_mode') or 0o644)


def uninstall(root):
    root = Path(root)
    with file_lock(root / 'state/desktop-integration.lock'):
        record = registration(root)
        if not record:
            return {'registered': False, 'message': 'No hay conexión registrada.'}
        if record.get('platform') != 'linux':
            raise DiscoveryError('La conexión registrada pertenece a otro sistema.')
        target = Path(record['target'])
        if target.exists():
            current = target.read_bytes()
            previous = base64.b64decode(record['previous']) if record['previous'] is not None else None
            if fingerprint(current) == record['installed_sha256']:
                restore_previous(record)
            elif current != previous:
                raise DiscoveryError('El acceso fue modificado por otra herramienta. Se ha conservado; no se ha desconectado automáticamente.')
        elif record['previous'] is not None:
            raise DiscoveryError('El acceso original fue eliminado externamente. Se conserva su copia de recuperación.')
        (root / 'state/desktop-integration.json').unlink()
    return {'registered': False, 'message': 'Inicio habitual restaurado. El historial y las claves se conservan. Se aplica al volver a abrir Desktop.'}


def app_running(installation):
    # Exact executable identity, never a title substring or a user command line.
    directory = installation.desktop.resolve().parent
    candidates = {directory / name for name in ('ChatGPT', 'chatgpt', 'Codex', 'codex-desktop')}
    for path in Path('/proc').glob('[0-9]*/exe'):
        try:
            if path.resolve(strict=True) in candidates:
                return True
        except (OSError, RuntimeError):
            continue
    return False
