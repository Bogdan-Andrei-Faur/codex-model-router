import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_identity import identity, router_identity


class BuildIdentityTests(unittest.TestCase):
    def test_ui_changes_do_not_request_backend_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'VERSION').write_text('0.3.1')
            (root / 'routing.py').write_text('policy = 1')
            (root / 'monitor-ui').mkdir()
            before, backend = identity(root), router_identity(root)
            for name in ('MonitorMac.swift', 'MonitorWpf.cs', 'MonitorWindows.cs', 'monitor_state.py', 'monitor_service.py', 'monitor_linux.py', 'updates.py', 'monitor-ui/monitor.js', 'monitor-ui/monitor.css'):
                (root / name).write_text('changed')
                self.assertNotEqual(identity(root), before)
                self.assertEqual(router_identity(root), backend)
            (root / 'routing.py').write_text('policy = 2')
            self.assertNotEqual(router_identity(root), backend)
            backend = router_identity(root)
            (root / 'BridgeMac.swift').write_text('native bridge changed')
            self.assertNotEqual(router_identity(root), backend)
            backend = router_identity(root)
            for name in ('Launcher.cs', 'InstalledLauncher.cs', 'WindowsLayout.cs'):
                (root/name).write_text('native Windows bridge changed')
                self.assertNotEqual(router_identity(root),backend)
                backend=router_identity(root)
            (root / 'build_stamp.py').write_text('generated = True')
            self.assertEqual(router_identity(root), backend)
            (root / 'VERSION').write_text('0.3.2')
            self.assertNotEqual(router_identity(root), backend)

    def test_frozen_uses_loaded_stamp_not_later_source(self):
        stamp = types.SimpleNamespace(PRODUCT_VERSION='0.3.1', BUILD_ID='product', ROUTER_BUILD_ID='engine')
        with patch.object(sys, 'frozen', True, create=True), patch.dict(sys.modules, build_stamp=stamp):
            self.assertEqual(identity(Path('/missing')), ('0.3.1', 'product'))
            self.assertEqual(router_identity(Path('/missing')), 'engine')
