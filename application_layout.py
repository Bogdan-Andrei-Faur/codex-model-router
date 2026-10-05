"""Immutable application resources and independent per-user data.

Source checkouts retain the historic layout unless explicitly overridden. Native
packages use an owned manifest and never resolve runtime paths from user config.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from state_store import atomic_json, file_lock

APP_ID = 'codex-model-router'
MANIFEST = 'application.json'


def code_root():
    return Path(os.environ.get('PERSONAL_CODEX_ROUTER_CODE_ROOT', Path(__file__).resolve().parent)).resolve()


def user_data_root(platform=None, home=None, environment=None):
    platform = platform or sys.platform
    home = Path(home or Path.home())
    env = os.environ if environment is None else environment
    if platform == 'darwin':
        return home / 'Library/Application Support' / APP_ID
    if platform == 'win32':
        return Path(env.get('LOCALAPPDATA') or home / 'AppData/Local') / APP_ID
    if platform == 'linux':
        base = env.get('XDG_DATA_HOME')
        return (Path(base) if base and Path(base).is_absolute() else home / '.local/share') / APP_ID
    raise ValueError('Sistema no compatible.')


def manifest(resources):
    path = Path(resources) / MANIFEST
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema') != 1 or value.get('layout') != 'macos-bundle-v1':
        raise ValueError('Manifiesto de instalación no compatible.')
    return value


def data_root(resources=None):
    explicit = os.environ.get('PERSONAL_CODEX_ROUTER_ROOT')
    if explicit:
        return Path(explicit).expanduser().resolve()
    resources = Path(resources or code_root())
    return user_data_root() if manifest(resources) else resources


def installed_path(resources, key):
    resources = Path(resources).resolve()
    value = manifest(resources)
    if not value or not isinstance(value.get(key), str):
        raise ValueError('Componente instalado no disponible.')
    # Manifest paths are relative to owned Contents; never user-config executables.
    relative = Path(value[key])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Ruta de instalación no válida.')
    destination = (resources.parent / relative).resolve()
    destination.relative_to(resources.parent)
    if not destination.is_file():
        raise ValueError('La instalación está incompleta.')
    return destination


def runtime_command(service, resources=None, root=None):
    resources = Path(resources or code_root())
    if manifest(resources):
        command = [str(installed_path(resources, 'runtime'))]
        if root is not None:
            command += ['--data-root', str(Path(root).resolve())]
        return command + [service]
    if service == 'desktop':
        if getattr(sys, 'frozen', False):
            return [str(resources / 'bin/codex-desktop-core.exe')]
        return [sys.executable, str(resources / 'desktop.py')]
    raise ValueError('Servicio no disponible en esta instalación.')


def bootstrap(resources, root, platform=None):
    """Create a private default config once. Never refresh existing user config."""
    resources, root = Path(resources), Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with file_lock(root / 'state/bootstrap.lock'):
        target = root / 'config.local.json'
        if target.exists():
            existing = json.loads(target.read_text(encoding='utf-8-sig'))
            if not isinstance(existing, dict) or existing.get('platform') != (platform or sys.platform):
                raise ValueError('La configuración existente pertenece a otra instalación.')
            return False
        config = json.loads((resources / 'config.example.json').read_text(encoding='utf-8'))
        for key in ('python', 'desktop_runtime', 'router_runtime', 'monitor_runtime'):
            config.pop(key, None)
        config.update(platform=platform or sys.platform, installation_mode='auto', comparison_engines=[])
        atomic_json(target, config)
        return True


def credential_namespace(root):
    root = Path(root).resolve()
    try:
        value = json.loads((root / 'state/credential-namespace.json').read_text())['namespace']
        if isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value):
            return value
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return hashlib.sha256(str(root).encode('utf-8')).hexdigest()
