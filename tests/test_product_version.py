import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from router import PRODUCT_VERSION, Router
from routing import DEFAULT_ROUTES


class ProductVersionTests(unittest.TestCase):
    def test_version_file_is_semantic_and_bridge_publishes_it(self):
        self.assertEqual(PRODUCT_VERSION, (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertRegex(PRODUCT_VERSION, r"^\d+\.\d+\.\d+$")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            config.write_text(json.dumps({"enabled": True, "routes": DEFAULT_ROUTES}), encoding="utf-8")
            router = Router(config, root / "state")
            router.log({"event": "version_test"})
            snapshot = json.loads(next((root / "state").glob("status-*.json")).read_text(encoding="utf-8"))
            self.assertEqual(snapshot["product_version"], PRODUCT_VERSION)
