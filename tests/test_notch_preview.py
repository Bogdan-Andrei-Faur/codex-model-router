"""Development preview isolation and matching native notch input geometry."""
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.monitor.monitor_state import MonitorState, notch_inset
from tools.preview_monitor import PreviewServer

ROOT = Path(__file__).resolve().parents[1]


class NotchPreviewTests(unittest.TestCase):
    def test_live_payload_is_read_only_without_updater_or_config_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'state').mkdir()
            config = {'enabled': True, 'updates_auto_check': True, 'jev': {'api_key': 'fixture-secret'}}
            (root / 'config.local.json').write_text(json.dumps(config))
            status = {'pid': os.getpid(), 'heartbeat': time.time(), 'threads': {'fixture': {'status': 'active'}}}
            (root / 'state/status-fixture.json').write_text(json.dumps(status))
            model = MonitorState(root, ROOT, read_only=True)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            try:
                with patch.object(model.updater, 'maybe_check', side_effect=AssertionError('Preview checked updates')):
                    value = model.payload(False)
                self.assertTrue(value['readOnly'])
                self.assertFalse(value['preview'])
                self.assertEqual(value['connections'], 1)
                self.assertIn('fixture', value['threads'])
                self.assertNotIn('fixture-secret', json.dumps(value))
                for action in ('config', 'taskMode', 'quality', 'update', 'connection'):
                    with self.subTest(action=action), self.assertRaises(ValueError):
                        model.action({'action': action, 'value': 'install', 'key': 'enabled'})
                with self.assertRaises(ValueError):
                    model.configure('enabled', False)
                with self.assertRaises(ValueError):
                    model.task_mode('fixture', 'manual')
                with self.assertRaises(ValueError):
                    model.quality('fixture', 'overall', 'adequate')
                self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            finally:
                model.close()

    def test_loopback_token_allowlist_origin_and_no_mutation_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            model = MonitorState(directory, ROOT, preview=True, read_only=True)
            with patch('socket.getfqdn', side_effect=AssertionError('Loopback preview performed DNS lookup')):
                server = PreviewServer(model)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(path, method='GET', headers=None):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                connection.request(method, path, headers=headers or {})
                response = connection.getresponse()
                result = response.status, response.read(), dict(response.getheaders())
                connection.close()
                return result
            try:
                self.assertEqual(request('/snapshot')[0], 404)
                self.assertEqual(request(server.prefix + '../config.local.json')[0], 404)
                self.assertEqual(request(server.prefix + 'snapshot', headers={'Origin': 'https://example.com'})[0], 404)
                self.assertEqual(request(server.prefix + 'snapshot', headers={'Host': 'example.com'})[0], 404)
                self.assertEqual(request(server.prefix + 'snapshot', 'POST')[0], 501)
                status, data, headers = request(server.prefix + 'snapshot')
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(data)['readOnly'])
                self.assertEqual(headers['Cache-Control'], 'no-store')
                html = request(server.prefix + 'index.html')[1].decode()
                self.assertIn('connect-src \'self\'', html)
                self.assertIn('preview.js', html)
                self.assertIn("font-src 'self'", html)
                status, font, headers = request(server.prefix + 'fonts/Nunito-variable.ttf')
                self.assertEqual(status, 200)
                self.assertEqual(headers['Content-Type'], 'font/ttf')
                self.assertEqual(font, (ROOT / 'monitor-ui/fonts/Nunito-variable.ttf').read_bytes())
                self.assertEqual(request(server.prefix + 'fonts/../config.local.json')[0], 404)
                self.assertIn("connect-src 'none'", (ROOT / 'monitor-ui/index.html').read_text())
            finally:
                server.shutdown()
                thread.join(3)
                server.server_close()
                model.close()

    def test_geometry_matches_concave_shoulders_body_and_bottom_corners(self):
        for height in (76, 300, 780):
            for width in (320, 390, 590):
                self.assertEqual(notch_inset(width, height, 0), 0)
                self.assertAlmostEqual(notch_inset(width, height, 10), 17.320508, places=5)
                self.assertEqual(notch_inset(width, height, 20), 20)
                self.assertEqual(notch_inset(width, height, height / 2), 20)
                self.assertEqual(notch_inset(width, height, height), 52)
                for y in range(height):
                    self.assertTrue(0 <= notch_inset(width, height, y) < width / 2)
