"""Offline release signing. Never uploads assets, keys, or changes GitHub visibility.

Use an encrypted Ed25519 PEM outside the checkout. The signing passphrase is
requested interactively and never accepted through a command-line/environment
argument. Public keys must separately be reviewed and shipped in the app.
"""
import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from codex_model_router.update_trust import DOMAIN, MANIFEST_NAME, MAX_VALIDITY, verify
from codex_model_router.updates import REPOSITORY, installer_name, version_key, MAX_PACKAGE


def encoded(value):
    return base64.b64encode(value).decode('ascii')


def public_entry(key):
    from cryptography.hazmat.primitives import serialization
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest(), encoded(raw)


class KeychainSigner:
    def __init__(self, helper):
        self.helper = str(Path(helper).resolve(strict=True))

    def public_key(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        raw = subprocess.check_output([self.helper, 'public'], timeout=60).strip()
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(raw, validate=True))

    def sign(self, payload):
        return base64.b64decode(subprocess.check_output([self.helper, 'sign'], input=payload, timeout=60).strip(), validate=True)


def write_new(path, data, mode=0o600):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def generate(path, password):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    if len(password) < 12:
        raise ValueError('Usa una contraseña de al menos 12 caracteres.')
    key = Ed25519PrivateKey.generate()
    write_new(path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.BestAvailableEncryption(password.encode('utf-8'))))
    key_id, public = public_entry(key)
    return {'schema': 1, 'keys': {key_id: public}}


def sign(key, version, artifacts, now=None, validity=30 * 86400):
    if version_key(version)[3] != 1 or not 0 < validity <= MAX_VALIDITY:
        raise ValueError('Versión o caducidad no válida.')
    entries = []
    for target, source in artifacts:
        platform, arch = target.split('/')
        path = Path(source)
        name = installer_name(version, platform, arch)
        if path.name != name or path.is_symlink() or not path.is_file():
            raise ValueError('Cada instalador debe tener su nombre canónico y ser un archivo regular.')
        before = path.stat()
        if not 0 < before.st_size <= MAX_PACKAGE:
            raise ValueError('Tamaño de instalador no válido.')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('El instalador cambió durante la firma.')
        entries.append({'platform': platform, 'arch': arch, 'name': name, 'size': before.st_size, 'sha256': digest.hexdigest()})
    now = int(time.time() if now is None else now)
    payload = json.dumps({'schema': 1, 'repository': REPOSITORY, 'version': version,
                          'created': now, 'expires': now + validity, 'assets': entries},
                         sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    key_id, public = public_entry(key)
    envelope = json.dumps({'schema': 1, 'keyId': key_id, 'payload': encoded(payload),
                           'signature': encoded(key.sign(DOMAIN + payload))}, sort_keys=True).encode('ascii')
    if not entries:
        raise ValueError('No hay instaladores para firmar.')
    for entry in entries:
        verify(envelope, {key_id: public}, dict(entry, version=version), entry['platform'], entry['arch'], now=now)
    return envelope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('keygen')
    create.add_argument('--private-key', type=Path, required=True)
    signing = sub.add_parser('sign')
    key_source = signing.add_mutually_exclusive_group(required=True)
    key_source.add_argument('--private-key', type=Path)
    key_source.add_argument('--keychain-helper', type=Path)
    signing.add_argument('--version', required=True)
    signing.add_argument('--asset', nargs=2, action='append', metavar=('PLATFORM/ARCH', 'PATH'), required=True)
    signing.add_argument('--output', type=Path, required=True)
    signing.add_argument('--valid-days', type=int, default=30)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.private_key and args.private_key.expanduser().resolve().is_relative_to(root):
        parser.error('La clave privada debe guardarse fuera del repositorio.')
    password = getpass.getpass('Contraseña de la clave de firma: ') if args.private_key else None
    if args.command == 'keygen':
        if password != getpass.getpass('Repite la contraseña: '):
            parser.error('Las contraseñas no coinciden.')
        print(json.dumps(generate(args.private_key, password), indent=2))
    else:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        if args.private_key and args.private_key.is_symlink():
            parser.error('La clave debe ser un archivo regular.')
        key = (load_pem_private_key(args.private_key.read_bytes(), password.encode('utf-8'))
               if args.private_key else KeychainSigner(args.keychain_helper))
        if not isinstance(key, (Ed25519PrivateKey, KeychainSigner)):
            parser.error('La clave debe ser Ed25519.')
        raw = sign(key, args.version, args.asset, validity=args.valid_days * 86400)
        write_new(args.output, raw + b'\n', mode=0o644)
        print(json.dumps({'signed': True, 'assets': len(args.asset), 'manifest': args.output.name}))


if __name__ == '__main__':
    main()
