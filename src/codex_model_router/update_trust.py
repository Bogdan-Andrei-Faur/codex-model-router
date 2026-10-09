"""Authenticate release bytes against keys shipped with the installed application.

GitHub hashes protect transport integrity; this independent Ed25519 signature
binds the repository, version, target, filename, size and digest. No downloaded
key, user configuration or receipt can grant trust. Private keys stay offline.
"""
import base64
import binascii
import hashlib
import json
import re
import time
from pathlib import Path

MANIFEST_NAME = 'codex-model-router-update.json'
MAX_ENVELOPE = 65536
MAX_VALIDITY = 180 * 86400
DOMAIN = b'codex-model-router/release-manifest/v1\x00'


class TrustError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise TrustError('invalid_signature')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (TypeError, ValueError, UnicodeError):
        raise TrustError('invalid_signature') from None


def decode(value, size=None):
    try:
        if not isinstance(value, str):
            raise ValueError()
        result = base64.b64decode(value, validate=True)
        if size is not None and len(result) != size:
            raise ValueError()
        return result
    except (ValueError, binascii.Error):
        raise TrustError('invalid_signature') from None


def load_keys(resources):
    """An empty installed keyring explicitly disables authenticated application."""
    path = Path(resources) / 'assets/update-trust.json'
    if not path.exists():
        return {}
    if path.is_symlink() or path.stat().st_size > MAX_ENVELOPE:
        raise TrustError('invalid_trust_store')
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1 or not isinstance(value.get('keys'), dict):
        raise TrustError('invalid_trust_store')
    keys = value['keys']
    if len(keys) > 8:
        raise TrustError('invalid_trust_store')
    for identifier, encoded in keys.items():
        raw = decode(encoded, 32)
        if identifier != hashlib.sha256(raw).hexdigest():
            raise TrustError('invalid_trust_store')
    return keys


def verify(raw, keys, package, platform, arch, now=None):
    from codex_model_router.updates import REPOSITORY, installer_name, UpdateError
    if not keys:
        raise TrustError('trust_unconfigured')
    if not isinstance(raw, bytes) or len(raw) > MAX_ENVELOPE:
        raise TrustError('invalid_signature')
    envelope = strict_json(raw)
    if (not isinstance(envelope, dict) or set(envelope) != {'schema', 'keyId', 'payload', 'signature'}
            or type(envelope['schema']) is not int or envelope['schema'] != 1):
        raise TrustError('invalid_signature')
    key_id = envelope['keyId']
    if not isinstance(key_id, str) or key_id not in keys:
        raise TrustError('unknown_publisher')
    payload = decode(envelope['payload'])
    signature = decode(envelope['signature'], 64)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        raise TrustError('signature_support_missing') from None
    try:
        Ed25519PublicKey.from_public_bytes(decode(keys[key_id], 32)).verify(signature, DOMAIN + payload)
    except (InvalidSignature, ValueError):
        raise TrustError('invalid_signature') from None
    value = strict_json(payload)
    if (not isinstance(value, dict) or set(value) != {'schema', 'repository', 'version', 'created', 'expires', 'assets'}
            or type(value['schema']) is not int or value['schema'] != 1
            or value['repository'] != REPOSITORY or value['version'] != package['version']):
        raise TrustError('invalid_signature')
    created, expires = value['created'], value['expires']
    now = time.time() if now is None else now
    if type(created) is not int or type(expires) is not int or not 0 < expires - created <= MAX_VALIDITY:
        raise TrustError('invalid_signature')
    if created > now + 300 or expires <= now:
        raise TrustError('signature_expired')
    assets = value['assets']
    if not isinstance(assets, list) or not 1 <= len(assets) <= 9:
        raise TrustError('invalid_signature')
    seen = set()
    selected = None
    for item in assets:
        if not isinstance(item, dict) or set(item) != {'platform', 'arch', 'name', 'size', 'sha256'}:
            raise TrustError('invalid_signature')
        try:
            name = installer_name(value['version'], item['platform'], item['arch'])
            target = (item['platform'], item['arch'])
            if target in seen:
                raise ValueError()
            seen.add(target)
        except (ValueError, TypeError, UpdateError):
            raise TrustError('invalid_signature') from None
        if (item['name'] != name or type(item['size']) is not int or not 0 < item['size'] <= 512 * 1024 * 1024
                or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise TrustError('invalid_signature')
        if target == (platform, arch):
            selected = item
    if selected is None or any(selected[key] != package[key] for key in ('name', 'size', 'sha256')):
        raise TrustError('signature_target_mismatch')
    return {'keyId': key_id, 'expires': expires}
