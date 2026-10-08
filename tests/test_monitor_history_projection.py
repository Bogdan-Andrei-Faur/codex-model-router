"""Compact history preserves the JS projection, append order and reset semantics."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from monitor_state import HistoryProjection, MonitorState

ROOT = Path(__file__).resolve().parents[1]


class HistoryProjectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for JS parity checks')
    def test_incremental_projection_matches_javascript_at_each_boundary(self):
        batches = [
            [{'event': 'decision_created', 'decision_id': 'd', 'thread': 't', 'time': 1, 'model': 'gpt-6-luna', 'effort': 'high', 'routing_engine': 'rules'},
             {'event': 'decision_routed', 'decision_id': 'd', 'routing_engine': 'rules', 'time': 2},
             {'event': 'engine_comparison', 'decision_id': 'd', 'routing_engine': 'jev', 'engine_active': False, 'engine_status': 'ok', 'proposed_model': 'gpt-6-astra', 'time': 3},
             {'event': 'decision_accepted', 'decision_id': 'd', 'accepted_model': 'gpt-6-luna', 'time': 4}],
            [{'event': 'inference_observed', 'decision_id': 'd', 'phase_id': 'p', 'observed_model': 'gpt-6-luna', 'observed_effort': 'high', 'evidence_confidence': 'confirmed', 'estimate_basis': 'standard_equivalent_not_billed', 'inference_event_id': 'i', 'estimated_api_standard_usd': 0.02, 'estimated_codex_standard_credits': 0.1, 'inference_model_mismatch': True, 'time': 5},
             {'event': 'inference_probable', 'decision_id': 'd', 'phase_id': 'p', 'observed_candidate_model': 'gpt-6-astra', 'evidence_confidence': 'probable', 'time': 6},
             {'event': 'inference_metric', 'decision_id': 'd', 'inference_event_name': 'request', 'inference_sample_count': 2, 'inference_failure_count': 1, 'inference_duration_ms': 20, 'time': 7},
             {'event': 'decision_usage', 'decision_id': 'd', 'inputTokens': 10, 'outputTokens': 2, 'time': 8},
             {'event': 'decision_usage_total', 'decision_id': 'd', 'inputTokens': 1000, 'outputTokens': 200, 'time': 9}],
            [{'event': 'phase_checkpoint', 'decision_id': 'd', 'phase_id': 'q', 'phase_status': 'applied', 'phase_model': 'gpt-6.1-sol', 'phase_effort': 'medium', 'time': 10},
             {'event': 'decision_usage', 'decision_id': 'd', 'outputTokens': 0, 'time': 11},
             {'event': 'native_turn_error', 'decision_id': 'd', 'will_retry': True, 'time': 12},
             {'event': 'decision_completed', 'decision_id': 'd', 'status': 'completed', 'time': 13},
             {'event': 'decision_quality', 'decision_id': 'd', 'model_quality': 'adequate', 'time': 14},
             {'event': 'decision_created', 'decision_id': 'other', 'time': '15'}],
        ]
        projection = HistoryProjection()
        events = []
        script = "const C=require('./monitor-ui/core.js'),fs=require('fs'),a=require('assert/strict');const x=JSON.parse(fs.readFileSync(0));a.deepEqual(JSON.parse(JSON.stringify(C.decisions(x.raw))),JSON.parse(JSON.stringify(C.decisions(x.compact))));"
        for batch in batches:
            events.extend(batch)
            projection.apply(batch)
            subprocess.run(['node', '-e', script], cwd=ROOT,
                           input=json.dumps({'raw': events, 'compact': projection.snapshot()}),
                           text=True, capture_output=True, check=True)
        self.assertEqual(projection.events_processed, len(events))

    def test_append_is_incremental_and_rotation_or_recovery_rebuilds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / 'state'
            state.mkdir()
            journal = state / 'history.jsonl'
            rows = [{'event': 'decision_created', 'decision_id': str(i), 'thread': 't', 'time': i} for i in range(1000)]
            journal.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            model = MonitorState(root, ROOT, read_only=True)
            try:
                first = model.payload(True, -1)
                projection = model.history_projection
                self.assertEqual(len(first['history']), 1000)
                with journal.open('a') as stream:
                    stream.write(json.dumps({'event': 'decision_quality', 'decision_id': '999', 'quality': 'adequate'})+'\n')
                model.payload(True, first['journalRevision'])
                self.assertIs(model.history_projection, projection)
                self.assertEqual(projection.events_processed, 1001)
                self.assertEqual(model.ui_history[-1]['record']['quality'], 'adequate')
                recovery = state / 'history.recovered.jsonl'
                recovery.write_text('{"event":"decision_recovered","decision_id":"999","status":"completed"}\n')
                model.load_history()
                self.assertTrue(model.ui_history[-1]['record']['accepted'])
                replacement = journal.with_suffix('.new')
                replacement.write_text('{"event":"decision_created","decision_id":"fresh","time":1}\n')
                replacement.replace(journal)
                recovery.unlink()
                model.load_history()
                self.assertEqual([r['record']['id'] for r in model.ui_history], ['fresh'])
                journal.unlink()
                model.load_history()
                self.assertEqual(model.ui_history, [])
            finally:
                model.close()


if __name__ == '__main__':
    unittest.main()
