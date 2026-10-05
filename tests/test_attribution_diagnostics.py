"""Completion diagnostics must preserve the boundary between evidence and guesses."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from zipfile import ZipFile

from inference_attribution import REJECTIONS
from inference_telemetry import safe_records
from router import Router
from tests.test_inference_telemetry import payload


class AttributionDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        config = root / 'config.json'
        config.write_text(json.dumps({'enabled': True}))
        self.router = Router(config, root / 'state')
        self.thread = 'thread_12345678'
        self.router.threads[self.thread] = dict(turn_id='turn-current', phase_status='active',
            status='inProgress', phase_model='gpt-6-luna', phase_effort='low', phase_pipeline=[])
        self.router.current_decisions[self.thread] = 'decision-current'

    def record(self, kind='response.completed', **changes):
        data = payload(model='gpt-6-luna', effort='low', kind=kind)
        log = data['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        log['attributes'] = [a for a in log['attributes'] if a['key'] != 'model_reasoning_effort']
        log.update(timeUnixNano='0', observedTimeUnixNano=str(time.time_ns()))
        record, = safe_records(data)
        return dict(record, **changes)

    def test_retry_packets_and_duplicate_completion_do_not_inflate_completion_coverage(self):
        self.router.observe_inference(self.record('response.failed'))
        record = self.record()
        self.router.observe_inference(record)
        self.router.observe_inference(record)
        stats = self.router.stats
        self.assertEqual(stats['telemetry_records'], 3)
        self.assertEqual(stats['telemetry_events'], 1)
        self.assertEqual(stats['telemetry_duplicates'], 1)
        self.assertEqual(stats['telemetry_missing_turn_id'], 2)
        for field in ('turn_id', 'response_id', 'effort'):
            self.assertEqual(stats['telemetry_completion_missing_' + field], 1)
        self.assertEqual(stats['telemetry_probable'], 1)
        self.assertEqual(stats['telemetry_confirmed'], 0)

    def test_completion_rejections_reconcile_without_relabelling_other_models(self):
        for record in (
            self.record(thread_id='unknown-thread'),
            self.record(turn_id='previous-turn'),
            self.record(model='gpt-6-astra'),
        ):
            self.router.observe_inference(record)
        self.router.observe_inference(self.record('response.failed', thread_id='unknown-thread'))
        stats = self.router.stats
        self.assertEqual(stats['telemetry_unattributed'], 3)
        self.assertEqual(sum(stats['telemetry_completion_' + r] for r in REJECTIONS), 3)
        for reason in ('unknown_thread', 'turn_mismatch', 'model_mismatch'):
            self.assertEqual(stats['telemetry_completion_' + reason], 1)
        self.assertEqual(stats['telemetry_unknown_thread'], 2)
        self.assertNotIn('observed_model', self.router.threads[self.thread])

    def test_compaction_does_not_invent_identity_and_exact_current_turn_still_confirms(self):
        params = dict(threadId=self.thread, turnId='turn-current',
                      item={'type': 'contextCompaction', 'id': 'compaction-one'})
        for method, state in (('item/started', 'compacting'), ('item/completed', 'awaiting_usage')):
            self.router.server_line(json.dumps({'method': method, 'params': params}))
            self.router.observe_inference(self.record())
            row = self.router.threads[self.thread]
            self.assertEqual(row['context_compaction']['state'], state)
            self.assertNotIn('observed_model', row)
        self.router.observe_inference(self.record(turn_id='previous-turn'))
        self.router.observe_inference(self.record(turn_id='turn-current', response_id='response-current'))
        self.assertEqual(self.router.stats['telemetry_probable'], 2)
        self.assertEqual(self.router.stats['telemetry_confirmed'], 1)
        self.assertEqual(self.router.stats['telemetry_completion_turn_mismatch'], 1)

    def test_export_keeps_completion_counts_without_exporting_private_snapshot_data(self):
        from evidence import export
        self.router.observe_inference(self.record(thread_id='unknown-thread'))
        snapshot = dict(stats=self.router.stats, heartbeat=time.time(),
                        threads={'private-thread': {'name': 'PRIVATE_TITLE'}})
        (self.router.state_dir / 'status-1.json').write_text(json.dumps(snapshot))
        output = Path(self.scratch.name) / 'evidence.zip'
        export(self.router.state_dir, output, 'ubuntu')
        with ZipFile(output) as archive:
            data = archive.read('snapshots.json').decode()
        self.assertNotIn('private-thread', data)
        self.assertNotIn('PRIVATE_TITLE', data)
        counters = json.loads(data)[0]['stats']
        self.assertEqual(counters['telemetry_completion_unknown_thread'], 1)
        self.assertEqual(counters['telemetry_completion_missing_turn_id'], 1)
