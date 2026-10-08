"""Secret Service adapter. Secret values only cross anonymous pipes, never argv."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import uuid

PROVIDERS = ('jev-typesafe', 'jev-vercel')
_CACHE = {}


def attributes(root, provider):
    if provider not in PROVIDERS:
        raise ValueError('Unknown provider')
    from codex_model_router.platforms.application_layout import credential_namespace
    return {'installation': credential_namespace(root), 'provider': provider}


def request(root, action, provider, value=None):
    if provider not in PROVIDERS or action not in ('read', 'store', 'present', 'clear'):
        return None
    # The bridge may use a venv without PyGObject. Ubuntu's system interpreter
    # owns the distribution's GI bindings; no import changes to the shared core.
    try:
        result = subprocess.run(['/usr/bin/python3', '-I', '-B', '-c',
                                'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); '
                                'runpy.run_module("codex_model_router.platforms.linux_secret",run_name="__main__")',
                                str(Path(__file__).resolve().parents[2]), action, str(Path(root).resolve()), provider],
                                input=value or '', text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=45 if action == 'store' else 5)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def read_key(state, provider):
    state = Path(state)
    try:
        revision = json.loads((state / 'keychain-revision.json').read_text()).get(provider)
    except (OSError, ValueError, AttributeError):
        revision = None
    key = (str(state.resolve()), provider)
    cached = _CACHE.get(key)
    if cached and cached[0] == revision:
        return cached[1]
    value = request(state.parent, 'read', provider)
    if value:
        _CACHE[key] = (revision, value)
    return value


def store_key(root, provider, value):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) >= 16384:
        return False
    if request(root, 'store', provider, value.strip()) != 'ok':
        return False
    from codex_model_router.storage.state_store import atomic_json, file_lock
    state = Path(root) / 'state'
    with file_lock(state / 'keychain-revision.lock'):
        try:
            revisions = json.loads((state / 'keychain-revision.json').read_text())
        except (OSError, ValueError):
            revisions = {}
        revisions[provider] = uuid.uuid4().hex
        atomic_json(state / 'keychain-revision.json', revisions)
    return True


def main():
    import gi
    gi.require_version('Secret', '1')
    from gi.repository import Gio, Secret
    action, root, provider = sys.argv[1:]
    attrs = attributes(root, provider)
    schema = Secret.Schema.new('local.codex-model-router', Secret.SchemaFlags.NONE,
                               {'installation': Secret.SchemaAttributeType.STRING, 'provider': Secret.SchemaAttributeType.STRING})
    cancel = Gio.Cancellable()
    timer = threading.Timer(40 if action == 'store' else 4, cancel.cancel)
    timer.daemon = True
    timer.start()
    try:
        if action == 'read':
            value = Secret.password_lookup_sync(schema, attrs, cancel)
            if value:
                sys.stdout.write(value)
        elif action == 'present':
            service = Secret.Service.get_sync(Secret.ServiceFlags.NONE, cancel)
            items = service.search_sync(schema, attrs, Secret.SearchFlags.NONE, cancel)
            sys.stdout.write('yes' if items else 'no')
        elif action == 'clear':
            Secret.password_clear_sync(schema, attrs, cancel)
            sys.stdout.write('ok')
        elif action == 'store':
            value = sys.stdin.read(16384)
            if not value or len(value.encode()) >= 16384:
                return 1
            if not Secret.password_store_sync(schema, attrs, Secret.COLLECTION_DEFAULT, 'Codex automático · ' + provider, value, cancel):
                return 1
            sys.stdout.write('ok')
        else:
            return 1
    finally:
        timer.cancel()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # Never include a secret-bearing exception in diagnostics.
        raise SystemExit(1)
