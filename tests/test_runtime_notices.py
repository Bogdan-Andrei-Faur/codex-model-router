import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.packaging import bundled_notices, prepare_runtime_notices as notices


class RuntimeNoticesTests(unittest.TestCase):
    def test_download_publishes_verified_bytes_and_reuses_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder); data = b'verified archive'
            digest = hashlib.sha256(data).hexdigest()
            with patch.object(notices.urllib.request, 'urlopen', return_value=io.BytesIO(data)) as network:
                target = notices.fetch('https://example.invalid/archive', digest, cache)
                self.assertEqual(target.read_bytes(), data)
                self.assertEqual(notices.fetch('https://example.invalid/archive', digest, cache), target)
                network.assert_called_once()
            self.assertEqual(list(cache.iterdir()), [target])

    def test_network_failure_closes_and_removes_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            with patch.object(notices.urllib.request, 'urlopen', side_effect=OSError('synthetic network failure')):
                with self.assertRaisesRegex(OSError, 'synthetic network failure'):
                    notices.fetch('https://example.invalid/archive', '0' * 64, cache)
            self.assertEqual(list(cache.iterdir()), [])

    def test_download_rejects_hash_or_size_and_does_not_leave_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder); digest = hashlib.sha256(b'expected').hexdigest()
            for data, limit in ((b'wrong', 100), (b'expected', 3)):
                with patch.object(notices.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                    with self.assertRaises(ValueError):notices.fetch('https://example.invalid/archive', digest, cache, limit=limit)
                self.assertEqual(list(cache.iterdir()), [])

    def test_nested_license_names_survive_and_traversal_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); archive = root / 'source.tar'
            def make(names):
                with tarfile.open(archive, 'w') as tar:
                    for name in names:
                        info = tarfile.TarInfo(name); info.size = 7;tar.addfile(info, io.BytesIO(b'license'))
            make(['crate/LICENSE', 'crate/vendor/LICENSE', 'crate/source.rs'])
            self.assertEqual(notices.texts(archive, root / 'out'), ['LICENSE','vendor/LICENSE'])
            make(['crate/../../LICENSE'])
            with self.assertRaises(ValueError):notices.texts(archive, root / 'unsafe')
            self.assertFalse((root.parent / 'LICENSE').exists())

    def test_offline_copy_rejects_changed_or_escaping_notices(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'share/router-build-notices';source.mkdir(parents=True)
            (root/'router-runtime-provenance.json').write_text('{}')
            (source/'LICENSE').write_text('expected')
            inventory=dict(python=sys.version.split()[0],runtime={},sourceHashes={},versions={},
                           files={'LICENSE':hashlib.sha256(b'expected').hexdigest()})
            (source/'inventory.json').write_text(json.dumps(inventory))
            with patch.object(bundled_notices.sys,'prefix',str(root)),patch.object(bundled_notices.sys,'base_prefix',str(root)):
                self.assertEqual(bundled_notices.copy_portable_notices(root/'good'),1)
                (source/'LICENSE').write_text('changed')
                with self.assertRaises(ValueError):bundled_notices.copy_portable_notices(root/'changed')
                self.assertFalse((root/'changed').exists())
                inventory['files']={'../../../router-runtime-provenance.json':hashlib.sha256(b'{}').hexdigest()}
                (source/'inventory.json').write_text(json.dumps(inventory))
                with self.assertRaises(ValueError):bundled_notices.copy_portable_notices(root/'escaping')


if __name__ == '__main__':unittest.main()
