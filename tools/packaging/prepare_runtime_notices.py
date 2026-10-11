"""Collect notices for the exact build interpreter/wheels before offline packaging.

Archives are downloaded from upstream, matched to pinned/SBOM SHA-256, and read
without executing or extracting source paths. The notice set is a conservative
superset (including build/all-target dependencies), not a claim all are linked.
"""
import argparse
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ('cryptography', 'cffi', 'pycparser', 'pyinstaller')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(url, sha256, cache, limit=100_000_000, size=None):
    if not re.fullmatch('[0-9a-f]{64}', sha256) or not url.startswith('https://'):
        raise ValueError('Invalid upstream notice input')
    target = cache / sha256
    if not target.exists():
        f = tempfile.NamedTemporaryFile(dir=cache, delete=False)
        partial = Path(f.name)
        try:
            with f:
                with urllib.request.urlopen(url, timeout=30) as r:
                    total = 0
                    while chunk := r.read(1024 * 1024):
                        total += len(chunk)
                        if total > limit: raise ValueError('Notice archive is too large')
                        f.write(chunk)
            # Windows forbids replacing/unlinking a NamedTemporaryFile while
            # its handle is open, including rejection and network-error paths.
            if digest(partial) != sha256: raise ValueError('Upstream notice hash mismatch')
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    if digest(target) != sha256 or (size is not None and target.stat().st_size != size):
        raise ValueError('Cached notice input mismatch')
    return target


def texts(archive, destination, excluded=()):
    copied = []
    with tarfile.open(archive) as tar:
        for member in tar:
            name = Path(member.name).name
            if name in excluded: continue
            if not member.isfile() or not re.match(r'(?i)^(license|licence|copying|copyright|notice)([._-]|$)', name):
                continue
            if member.size > 8_000_000: raise ValueError('Unexpected license size')
            # Preserve nested notices, without allowing archive path traversal.
            relative = Path(*Path(member.name).parts[1:])
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe license path')
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
            copied.append(relative.as_posix())
    if not copied: raise ValueError('Upstream archive has no license texts')
    return copied


def collect(destination, cache):
    if destination.exists(): raise ValueError('Use a new notice destination')
    cache.mkdir(parents=True, exist_ok=True)
    runtime = Path(sys.base_prefix)
    provenance = json.loads((runtime / 'router-runtime-provenance.json').read_text())
    metadata = json.loads((runtime / 'share/router-runtime-licenses/PYTHON.json').read_text())
    if metadata['python_version'] != sys.version.split()[0]: raise ValueError('Interpreter provenance mismatch')
    lock = json.loads((ROOT / 'tools/packaging/runtime-notices.lock.json').read_text())
    source_hashes, versions, components = {}, {}, []
    destination.mkdir(parents=True)
    runtime_texts = runtime / 'share/router-runtime-licenses'
    for name, sha in json.loads((runtime_texts / 'files.json').read_text()).items():
        if Path(name).name != name or digest(runtime_texts / name) != sha:
            raise ValueError('Prepared runtime notice changed')
    shutil.copytree(runtime / 'share/router-runtime-licenses', destination / 'python')
    (destination / 'python/provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    for name in PACKAGES:
        package = distribution(name); versions[name] = package.version
        copied = 0
        for item in package.files or []:
            if '.dist-info/' not in str(item) or not any(s in str(item).lower() for s in ('license', 'copying', '/sboms/')):
                continue
            source = Path(package.locate_file(item)); source_hashes[str(item)] = digest(source)
            if '/sboms/' not in str(item):
                target = destination / name / Path(*item.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
                copied += 1
        if not copied: raise ValueError('Dependency license missing: ' + name)
    package = distribution('cryptography')
    def sbom(suffix):
        return json.loads(package.locate_file(next(f for f in package.files if str(f).endswith(suffix))).read_text())
    for component in sbom('/cryptography-rust.cyclonedx.json')['components']:
        name, version = component['name'], component['version']
        if name.startswith('cryptography-') and 'file://' in component.get('purl', ''):
            continue  # Covered by cryptography's own Apache/BSD notices.
        if not re.fullmatch('[a-zA-Z0-9_-]+', name) or not re.fullmatch('[0-9A-Za-z.+-]+', version):
            raise ValueError('Invalid crate identity')
        sha = next(h['content'] for h in component['hashes'] if h['alg'] == 'SHA-256')
        url = f'https://static.crates.io/crates/{name}/{name}-{version}.crate'
        archive = fetch(url, sha, cache)
        files = texts(archive, destination / 'rust-crates' / (name + '-' + version))
        components.append(dict(name=name, version=version, sha256=sha, url=url, notices=files))
    openssl = next(c for c in sbom('/sbom.json')['components'] if c['name'] == 'openssl')
    sha = next(h['content'] for h in openssl['hashes'] if h['alg'] == 'SHA-256')
    url = f"https://github.com/openssl/openssl/releases/download/openssl-{openssl['version']}/openssl-{openssl['version']}.tar.gz"
    files = texts(fetch(url, sha, cache), destination / 'openssl')
    components.append(dict(name='openssl', version=openssl['version'], sha256=sha, url=url, notices=files))
    # The compiler's actual commit survives in the wheel's panic source paths.
    binary = package.locate_file(next(f for f in package.files if str(f).endswith('_rust.abi3.so')))
    commits = {m.decode() for m in re.findall(rb'/rustc/([0-9a-f]{40})/', binary.read_bytes())}
    rust = lock['rust']
    if commits != {rust['commit']}: raise ValueError('Rust compiler notices need review for this wheel')
    archive = fetch(rust['url'], rust['sha256'], cache, size=rust['size'])
    with tarfile.open(archive) as tar:
        member = next(m for m in tar if m.name.endswith('/git-commit-hash') and m.name.count('/') == 1)
        if tar.extractfile(member).read().decode().strip() != rust['commit']:
            raise ValueError('Rust notice archive is not the wheel compiler revision')
    texts(archive, destination / 'rust-standard-library', excluded=('COPYRIGHT.html',))
    source_hashes[str(next(f for f in package.files if str(f).endswith('_rust.abi3.so')))] = digest(binary)
    import compression.zstd
    if compression.zstd.zstd_version != '1.5.7': raise ValueError('Zstd notices need review')
    zstd = lock['zstd']
    shutil.copy2(fetch(zstd['url'], zstd['sha256'], cache, size=zstd['size']), destination / 'python/LICENSE.zstd.txt')
    inventory = dict(schema=1, versions=versions, python=sys.version.split()[0],
                     runtime=provenance, sourceHashes=source_hashes, components=components,
                     supplements=lock, scope='conservative upstream dependency notice superset',
                     files={str(p.relative_to(destination)): digest(p) for p in sorted(destination.rglob('*')) if p.is_file()})
    (destination / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    return dict(notices=len(inventory['files']), registryComponents=len(components), python=inventory['python'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('Use a new notice destination')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.notices-', dir=args.output.parent) as temporary:
        prepared = Path(temporary) / 'complete'
        report = collect(prepared, args.cache)
        prepared.rename(args.output)
    print(json.dumps(report))
