"""Copy the installed crypto dependency license texts into a frozen payload."""
from importlib.metadata import distribution
import hashlib
import json
from pathlib import Path
import shutil
import sys


def copy_portable_notices(destination):
    source = Path(sys.prefix) / 'share/router-build-notices'
    inventory = json.loads((source / 'inventory.json').read_text())
    if inventory['python'] != sys.version.split()[0]:
        raise ValueError('Prepared notices do not match build Python')
    provenance = Path(sys.base_prefix) / 'router-runtime-provenance.json'
    if inventory['runtime'] != json.loads(provenance.read_text()):
        raise ValueError('Prepared runtime provenance does not match')
    expected = inventory['sourceHashes']
    found = set()
    for name, version in inventory['versions'].items():
        package = distribution(name)
        if package.version != version: raise ValueError('Prepared notices differ from build dependencies')
        for item in package.files or []:
            if str(item) in expected:
                if hashlib.sha256(Path(package.locate_file(item)).read_bytes()).hexdigest() != expected[str(item)]:
                    raise ValueError('Dependency changed after notice preparation')
                found.add(str(item))
    if found != set(expected): raise ValueError('Prepared dependency input missing')
    for relative, digest in inventory['files'].items():
        path = source / relative
        if path.is_symlink() or source.resolve() not in path.resolve().parents or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Prepared notice is missing or changed')
    # No network and no unrelated files from the preparation directory enter the app.
    for relative in [*inventory['files'], 'inventory.json']:
        target = Path(destination) / 'runtime' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    return len(inventory['files'])


def copy_notices(destination):
    destination = Path(destination)
    count = 0
    for name in ('cryptography', 'cffi', 'pycparser', 'pyinstaller'):
        package = distribution(name)
        files = [p for p in package.files or [] if '.dist-info/' in str(p)
                 and ('license' in str(p).lower() or 'copying' in str(p).lower())]
        if not files:
            raise ValueError('Dependency license is missing: ' + name)
        for item in files:
            source = Path(package.locate_file(item))
            target = destination / name / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1
    return count


if __name__ == '__main__':
    print(copy_portable_notices(sys.argv[1]) if '--portable-macos' in sys.argv else copy_notices(sys.argv[1]))
