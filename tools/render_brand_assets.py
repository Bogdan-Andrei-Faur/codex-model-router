"""Export approved artwork to native icon containers without redrawing it.

Generation requires tools/requirements-brand.txt; --check uses only the standard
library. Never downloads images or changes installed applications.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'assets/brand'
SOURCE = ROOT / 'docs/design/brand/router-icon-v1.png'
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG image')
    return struct.unpack('>II', data[16:24])


def generate():
    from PIL import Image, __version__
    if __version__ != '11.3.0':
        raise ValueError('Use pinned tools/requirements-brand.txt')
    BRAND.mkdir(parents=True, exist_ok=True)
    # Keep the exact owner-approved pixels as the canonical master.
    (BRAND / 'router-source.png').write_bytes(SOURCE.read_bytes())
    with Image.open(SOURCE) as source:
        if source.width != source.height:
            raise ValueError('Brand master must be square')
        master = source.convert('RGBA')
        for size in (256, 1024):
            master.resize((size, size), Image.Resampling.LANCZOS).save(
                BRAND / ('router-' + str(size) + '.png'), optimize=True)
        master.save(BRAND / 'router.ico', format='ICO', sizes=[(n, n) for n in ICO_SIZES])
        master.resize((1024, 1024), Image.Resampling.LANCZOS).save(
            BRAND / 'router.icns', format='ICNS')
    files = {name: {'sha256': sha(BRAND / name), 'bytes': (BRAND / name).stat().st_size}
             for name in ('router-source.png', 'router-256.png', 'router-1024.png', 'router.ico', 'router.icns')}
    manifest = {'schema': 1, 'approved': '2026-10-09', 'generator': 'Pillow 11.3.0',
                'origin': 'Owner-approved built-in image_gen routing icon proposal; no input images',
                'palette': {'mint': '#87D8C2', 'gold': '#E6C585', 'lilac': '#C4AFE9'},
                'license': 'LicenseRef-Codex-Model-Router-Personal-Use-1.0', 'files': files}
    (BRAND / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def check():
    manifest = json.loads((BRAND / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        path = BRAND / name
        if sha(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError('Brand artifact changed: ' + name)
    if SOURCE.exists() and sha(SOURCE) != sha(BRAND / 'router-source.png'):
        raise ValueError('Brand master differs from approved artwork')
    for size in (256, 1024):
        if png_size((BRAND / ('router-' + str(size) + '.png')).read_bytes()) != (size, size):
            raise ValueError('Incorrect PNG size')
    data = (BRAND / 'router.ico').read_bytes()
    reserved, kind, count = struct.unpack('<HHH', data[:6])
    if (reserved, kind, count) != (0, 1, len(ICO_SIZES)):
        raise ValueError('Incorrect ICO directory')
    seen = []
    for index in range(count):
        w, h, _, _, planes, depth, length, offset = struct.unpack_from('<BBBBHHII', data, 6 + 16 * index)
        size = w or 256
        if (h or 256) != size or (planes, depth) != (0, 32) or offset + length > len(data):
            raise ValueError('Incorrect ICO entry')
        if png_size(data[offset:offset + length]) != (size, size):
            raise ValueError('ICO entry size mismatch')
        seen.append(size)
    if tuple(seen) != ICO_SIZES:
        raise ValueError('Missing ICO resolution')
    data = (BRAND / 'router.icns').read_bytes()
    if data[:4] != b'icns' or struct.unpack('>I', data[4:8])[0] != len(data):
        raise ValueError('Incorrect ICNS container')
    offset, types = 8, set()
    while offset < len(data):
        kind, length = struct.unpack_from('>4sI', data, offset)
        if length < 8 or offset + length > len(data):
            raise ValueError('Incorrect ICNS entry')
        types.add(kind); offset += length
    if offset != len(data) or not {b'ic07', b'ic08', b'ic09', b'ic10'} <= types:
        raise ValueError('Missing ICNS resolution')
    print(json.dumps({'pass': True, 'files': len(manifest['files']), 'icoSizes': seen,
                      'icns': True, 'approvedMasterPreserved': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        generate()
    check()
