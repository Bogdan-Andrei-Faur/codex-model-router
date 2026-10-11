"""Installation-scoped uploader credentials; no secrets in argv or config."""
import ctypes
import json
import os
import sys
from pathlib import Path
from codex_model_router.platforms.application_layout import credential_namespace
from codex_model_router.storage.state_store import private_open


def credential(root, value=None):
    root = Path(root)
    account = b'central-telemetry'
    if sys.platform == 'darwin':
        security = ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security')
        service = ('local.codex-model-router.' + credential_namespace(root)).encode()
        pointer = ctypes.c_void_p()
        length = ctypes.c_uint32()
        security.SecKeychainFindGenericPassword.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
        status = security.SecKeychainFindGenericPassword(None, len(service), service, len(account), account, ctypes.byref(length), ctypes.byref(pointer), None)
        if status == 0:
            try:
                return json.loads(ctypes.string_at(pointer, length.value))
            finally:
                security.SecKeychainItemFreeContent(None, pointer)
        if status != -25300 or value is None:  # errSecItemNotFound
            if status == -25300:
                return None
            raise OSError('credential_unavailable')
        raw = json.dumps(value).encode()
        security.SecKeychainAddGenericPassword.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_void_p]
        if security.SecKeychainAddGenericPassword(None, len(service), service, len(account), account, len(raw), raw, None):
            raise OSError('credential_unavailable')
        return value
    if os.name == 'nt':
        from ctypes import wintypes
        class Blob(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]
        path = root / 'state/central-telemetry.secret'
        reading = path.exists()
        if not reading and value is None:
            return None
        raw = path.read_bytes() if reading else json.dumps(value).encode()
        buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
        source, target = Blob(len(raw), buffer), Blob()
        function = ctypes.windll.crypt32.CryptUnprotectData if reading else ctypes.windll.crypt32.CryptProtectData
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise OSError('credential_unavailable')
        try:
            result = ctypes.string_at(target.data, target.size)
            if reading:
                return json.loads(result)
            with private_open(path, 'wb') as stream:
                stream.write(result)
            return value
        finally:
            ctypes.windll.kernel32.LocalFree(target.data)
    from codex_model_router.platforms.linux_secret import request
    raw = request(root, 'read', account.decode())
    if raw:
        return json.loads(raw)
    if value is not None and request(root, 'store', account.decode(), json.dumps(value)) == 'ok':
        return value
    if value is not None:
        raise OSError('credential_unavailable')
    return None
