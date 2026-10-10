"""Prepare a pinned portable build interpreter and its upstream license texts.

Developer-only download; never changes system Python or an installed application.
The full upstream archive supplies licensing metadata omitted by install_only.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def download(asset, cache):
    target = cache / asset['name']
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=cache, prefix='.runtime-', delete=False) as output:
            partial = Path(output.name)
            try:
                with urllib.request.urlopen(asset['browser_download_url'], timeout=30) as incoming:
                    size = 0
                    while True:
                        chunk = incoming.read(1024 * 1024)
                        if not chunk: break
                        size += len(chunk)
                        if size > asset['size']: raise ValueError('Runtime archive exceeds pinned size')
                        output.write(chunk)
                output.flush()
                if size != asset['size'] or hashlib.sha256(partial.read_bytes()).hexdigest() != asset['digest'][7:]:
                    raise ValueError('Runtime archive does not match pinned bytes')
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
    if target.stat().st_size != asset['size'] or hashlib.sha256(target.read_bytes()).hexdigest() != asset['digest'][7:]:
        raise ValueError('Cached runtime does not match pinned bytes')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin': raise ValueError('A native Mac is required')
    target = {'arm64': 'aarch64', 'x86_64': 'x86_64'}[platform.machine()]
    lock = json.loads((ROOT / 'tools/packaging/macos-runtime.lock.json').read_text())
    selected = lock['targets'][target]
    if args.output.exists(): raise ValueError('Use a new output directory; existing runtimes are preserved')
    args.cache.mkdir(parents=True, exist_ok=True)
    install = download(selected['install'], args.cache)
    full = download(selected['full'], args.cache)
    args.output.mkdir(parents=True)
    # Both archives were matched to immutable upstream bytes before extraction.
    subprocess.run(['/usr/bin/tar', '-xzf', str(install.resolve()), '-C', str(args.output.resolve())], check=True)
    python = args.output.resolve() / 'python/bin/python3'
    script = r'''
import hashlib,json,sys,tarfile
from pathlib import Path
archive,destination=map(Path,sys.argv[1:]); destination.mkdir(parents=True)
with tarfile.open(archive) as tar:
    metadata=json.load(tar.extractfile('python/PYTHON.json'))
    files={}
    for member in tar:
        if member.name.startswith('python/licenses/') and member.isfile():
            name=Path(member.name).name; data=tar.extractfile(member).read()
            (destination/name).write_bytes(data);files[name]=hashlib.sha256(data).hexdigest()
    (destination/'PYTHON.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (destination/'files.json').write_text(json.dumps(files,indent=2)+'\n')
'''
    licenses = args.output.resolve() / 'python/share/router-runtime-licenses'
    subprocess.run([str(python), '-c', script, str(full.resolve()), str(licenses)], check=True)
    metadata = json.loads((licenses / 'PYTHON.json').read_text())
    if metadata['python_version'] != lock['version'] or metadata['target_triple'] != target + '-apple-darwin':
        raise ValueError('Runtime metadata differs from pinned interpreter')
    receipt = {'schema': 1, 'provider': 'astral-sh/python-build-standalone', 'version': lock['version'],
               'release': lock['release'], 'target': target, 'archives': selected}
    (args.output / 'python/router-runtime-provenance.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'python': str(python), 'version': lock['version'], 'target': target,
                      'archiveIntegrityVerified': True, 'globalPythonChanged': False}))


if __name__ == '__main__': main()
