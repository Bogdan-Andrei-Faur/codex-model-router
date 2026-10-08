"""Cosmetic persistence is independent of routing and other agent identities."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.monitor.monitor_state import MonitorState, appearance_value
from codex_model_router.monitor.monitor_service import dispatch

ROOT = Path(__file__).resolve().parents[1]
LOOK = dict(name='Milo', color='#ff9e88', accessoryColor='#51698b', roundness=21,
            eyes='oval', head='cap', glasses=True, scarf=False)


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.model = MonitorState(self.root, ROOT, platform='macos')

    def tearDown(self):
        self.model.close()
        self.temp.cleanup()

    def save(self, thread, value=LOOK):
        return dispatch(self.model, dict(requestId=1, action='appearance', thread=thread, value=value))

    def test_independent_restart_and_reset_without_routing_writes(self):
        self.save('agent-a')
        self.save('agent-b', dict(LOOK, name='Lumi', color='#81d7bd'))
        other = MonitorState(self.root, ROOT, platform='windows')
        try:
            self.assertEqual(other.payload(False)['appearances']['agent-a'], appearance_value(LOOK))
            other.action(dict(action='appearance', thread='agent-a', value=None))
            values = self.model.payload(False)['appearances']
            self.assertNotIn('agent-a', values)
            self.assertEqual(values['agent-b']['name'], 'Lumi')
            self.assertFalse((self.root/'config.local.json').exists())
            self.assertFalse((self.root/'state/history.jsonl').exists())
        finally:
            other.close()

    def test_legacy_and_catalogue_slots_survive_restart(self):
        self.save('legacy', dict(LOOK, scarf=True))
        legacy = self.model.payload(False)['appearances']['legacy']
        self.assertEqual((legacy['glasses'], legacy['neck'], legacy['outfit']), ('rectangle', 'scarf', 'none'))
        look = dict(legacy, head='headphones', glasses='visor', outfit='labcoat', neck='bowtie', detail='pin')
        self.save('new', look)
        other = MonitorState(self.root, ROOT, platform='linux')
        try:
            self.assertEqual(other.payload(False)['appearances']['new'], look)
            for key in ('head', 'glasses', 'outfit', 'neck', 'detail'):
                with self.assertRaises(ValueError):
                    self.save('new', dict(look, **{key: 'unknown-item'}))
            self.assertEqual(other.payload(False)['appearances']['new'], look)
        finally:
            other.close()

    def test_invalid_input_keeps_last_saved_design(self):
        self.save('agent-a')
        path = self.root/'state/agent-appearances.json'
        before = path.read_bytes()
        for patch in [dict(color='url(private)'), dict(name='a\nb'), dict(name=''),
                      dict(roundness=True), dict(head='path/to.svg'), dict(glasses='yes'),
                      dict(extra='not allowed'), dict(eyes=[]), dict(roundness=100)]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.save('agent-a', dict(LOOK, **patch))
            self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.model.action(dict(action='appearance', thread='agent-a'))
        self.assertEqual(path.read_bytes(), before)

    def test_corrupt_or_newer_file_is_not_overwritten(self):
        path = self.root/'state/agent-appearances.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        for text in ['{broken', '{"version":2,"agents":{}}', '[]']:
            path.write_text(text)
            with self.assertRaises(ValueError):
                self.save('agent-a')
            self.assertEqual(path.read_text(), text)
            self.assertEqual(self.model.payload(False)['appearances'], {})

    def test_preview_and_read_only_cannot_write(self):
        for mode in [dict(preview=True), dict(read_only=True)]:
            model = MonitorState(self.root, ROOT, platform='linux', **mode)
            try:
                with self.assertRaises(ValueError):
                    model.action(dict(action='appearance', thread='agent-a', value=LOOK))
            finally:
                model.close()
        self.assertFalse((self.root/'state/agent-appearances.json').exists())

    def test_concurrent_monitors_preserve_different_agents(self):
        other = MonitorState(self.root, ROOT, platform='linux')
        try:
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(model.action, dict(action='appearance', thread=str(i), value=LOOK))
                           for i, model in enumerate([self.model, other])]
                for future in futures:
                    future.result()
            self.assertEqual(set(self.model.payload(False)['appearances']), {'0', '1'})
        finally:
            other.close()


if __name__ == '__main__':
    unittest.main()
