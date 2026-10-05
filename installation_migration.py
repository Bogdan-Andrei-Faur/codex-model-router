"""Guarded offline import into a new data root; source data is never overwritten.

This imports known product data, not a repository/build tree. It does not transfer
Desktop registration, activate a bridge, close apps or decrypt any credentials.
Coordination lock files may be created in the source state directory.
"""
from contextlib import ExitStack
import json
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


def reject_active(state):
    from monitor_state import alive
    for path in state.glob('status-*.json'):
        if path.is_symlink(): raise ValueError('La instalación contiene enlaces no compatibles.')
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            raise ValueError('No se puede confirmar que la instalación esté inactiva.') from None
        if not isinstance(record,dict) or type(record.get('pid')) is not int or record['pid'] <= 0:
            raise ValueError('No se puede confirmar que la instalación esté inactiva.')
        if alive(record['pid']):
            raise ValueError('La instalación sigue en uso. No se han importado ni modificado sus datos.')


def copy_stable(source, destination):
    if source.is_symlink() or not source.is_file():
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


def import_legacy(source, destination, platform=None):
    source = Path(source).expanduser()
    destination = Path(destination).expanduser()
    if source.is_symlink() or destination.is_symlink(): raise ValueError('La ruta de instalación no es válida.')
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('La instalación y el destino deben ser independientes.')
    if destination.exists(): raise ValueError('El destino ya contiene datos; no se han sustituido.')
    config_path=source/'config.local.json'; state=source/'state'
    if config_path.is_symlink() or state.is_symlink(): raise ValueError('La instalación contiene enlaces no compatibles.')
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    if not isinstance(config,dict) or config.get('platform') != (platform or sys.platform):
        raise ValueError('La configuración pertenece a otro sistema.')
    reject_active(state)
    destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.router-import-',dir=destination.parent))
    committed=False
    try:
        with ExitStack() as locks:
            locks.enter_context(file_lock(destination.parent/'.router-import.lock'))
            for name in ('config.lock','history.lock','prompts.lock','workloads.lock','monitor-mac.lock'):
                locks.enter_context(file_lock(state/name,timeout=.1))
            reject_active(state)
            copy_stable(config_path,temporary/'config.local.json')
            count=1
            for name in FILES:
                path=state/name
                if path.exists() or path.is_symlink(): copy_stable(path,temporary/'state'/name);count+=1
            for name in DIRECTORIES:
                directory=state/name
                if directory.is_symlink(): raise ValueError('La instalación contiene enlaces no compatibles.')
                if not directory.exists():continue
                for path in directory.iterdir():
                    if path.is_symlink() or not re.fullmatch('[0-9a-f]{64}\.json',path.name):
                        raise ValueError('La instalación contiene datos de tareas no compatibles.')
                    copy_stable(path,temporary/'state'/name/path.name);count+=1
            # Retain Keychain/Secret Service identity without ever retrieving keys.
            atomic_json(temporary/'state/credential-namespace.json',{'namespace':credential_namespace(source)})
            atomic_json(temporary/'state/migration.json',{'schema':1,'filesImported':count,'integrationPending':True,'sourcePreserved':True})
            reject_active(state)
            if destination.exists():raise ValueError('El destino cambió; no se han sustituido sus datos.')
            os.rename(temporary,destination);committed=True
        return {'imported':True,'filesImported':count,'integrationPending':True,'sourcePreserved':True}
    finally:
        if not committed:shutil.rmtree(temporary)
