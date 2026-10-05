"""Fetch the pinned official WebView2 SDK; verify every cached build input."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.4258.31'
URL = 'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/' + VERSION + '/microsoft.web.webview2.' + VERSION + '.nupkg'
SHA256 = '56f7f4b8bf9aee4b8efefbbdd4f67d5f74ebd1b100ed0806da71bf76af481aa9'


def prepare(destination):
    lock = json.loads((ROOT / 'tools/webview2-sdk.lock.json').read_text())
    files = lock['files']
    if all((destination / name).is_file() and hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest
           for name, digest in files.items()):
        return destination
    with urllib.request.urlopen(URL, timeout=60) as response:
        payload = response.read(32 * 1024 * 1024 + 1)
    if hashlib.sha256(payload).hexdigest() != SHA256:
        raise ValueError('Official SDK package checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name, digest in files.items():
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('SDK assembly checksum mismatch')
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.new')
            temporary.write_bytes(data)
            temporary.replace(target)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / ('state/webview2-sdk-' + VERSION))
    args = parser.parse_args()
    print(prepare(args.output))
