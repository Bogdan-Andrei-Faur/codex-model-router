"""HTTP regressions for large native OTLP batches; synthetic content only."""
import gzip
import http.client
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inference_telemetry import LocalInferenceTelemetry, MAX_WIRE_BYTES, MAX_DECODED_BYTES
from test_inference_telemetry import payload


class TelemetryBatchTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.collector = LocalInferenceTelemetry(self.events.append)
        self.addCleanup(self.collector.close)

    def post(self, body, encoding=None, length=None, authorized=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.collector.server.server_port, timeout=5)
        try:
            connection.putrequest('POST', '/v1/logs')
            connection.putheader('Authorization', 'Bearer ' + (self.collector.token if authorized else 'wrong'))
            if length != 'missing':
                connection.putheader('Content-Length', str(len(body) if length is None else length))
            if encoding:
                connection.putheader('Content-Encoding', encoding)
            connection.endheaders(body)
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def assert_private_content_absent(self):
        saved = json.dumps([self.events, self.collector.snapshot()])
        for text in ('PRIVATE_PROMPT', 'PRIVATE_ERROR', 'private@example.invalid', self.collector.token):
            self.assertNotIn(text, saved)

    def test_native_shaped_512_record_batch_survives_old_limit(self):
        sample = payload()
        record = sample['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        logs = []
        for index in range(512):
            logs.append(dict(record, timeUnixNano=str(1790528000000000000 + index)))
        sample['resourceLogs'][0]['scopeLogs'][0]['logRecords'] = logs
        raw = json.dumps(sample).encode()
        self.assertGreater(len(raw), 512 * 1024)
        for encoding, body in ((None, raw), ('gzip', gzip.compress(raw))):
            with self.subTest(encoding=encoding):
                self.assertEqual(self.post(body, encoding), 200)
        self.assertEqual(len(self.events), 1024)
        self.assertEqual(self.collector.snapshot()['completion_records'], 1024)
        self.assertEqual(self.collector.snapshot()['invalid_requests'], 0)
        self.assert_private_content_absent()

    def test_larger_gzip_batch_and_both_exact_limits(self):
        raw = json.dumps(payload()).encode()
        for limit, encoding in ((MAX_WIRE_BYTES, None), (MAX_DECODED_BYTES, 'gzip')):
            batch = raw + b' ' * (limit - len(raw))
            self.assertEqual(self.post(gzip.compress(batch) if encoding else batch, encoding), 200)
        health = self.collector.snapshot()
        self.assertEqual(len(self.events), 2)
        self.assertEqual(health['size_wire_4m'], 1)
        self.assertEqual(health['size_decoded_16m'], 1)
        self.assertEqual(health['invalid_size'], 0)

    def test_wire_and_expansion_rejections_are_distinct_and_recover(self):
        self.assertEqual(self.post(b'', length=MAX_WIRE_BYTES + 1), 413)
        expanded = b' ' * MAX_DECODED_BYTES
        # The budget applies across concatenated gzip members too.
        self.assertEqual(self.post(gzip.compress(expanded) + gzip.compress(b' '), 'gzip'), 413)
        health = self.collector.snapshot()
        self.assertEqual(health['invalid_wire_size'], 1)
        self.assertEqual(health['invalid_decoded_size'], 1)
        self.assertEqual(health['invalid_size'], 2)
        self.assertEqual(health['size_wire_16m'], 1)
        self.assertEqual(health['size_decoded_over16m'], 1)
        self.assertEqual(health['requests'], 0)
        self.assertEqual(self.events, [])
        self.assertEqual(self.post(json.dumps(payload()).encode()), 200)
        self.assertEqual(len(self.events), 1)
        self.assert_private_content_absent()

    def test_bad_lengths_are_not_reported_as_oversized(self):
        for length in ('missing', '0', '-1', 'invalid'):
            self.assertEqual(self.post(b'', length=length), 400)
        self.assertEqual(self.collector.snapshot()['invalid_length'], 4)
        self.assertEqual(self.collector.snapshot()['invalid_size'], 0)

    def test_malformed_batch_is_atomic_and_not_counted_as_processed(self):
        sample = payload()
        sample['resourceLogs'][0]['scopeLogs'][0]['logRecords'].append(None)
        self.assertEqual(self.post(json.dumps(sample).encode()), 400)
        health = self.collector.snapshot()
        self.assertEqual(health['invalid_payload'], 1)
        self.assertEqual(health['requests'], 0)
        self.assertEqual(health['records_scanned'], 0)
        self.assertEqual(self.events, [])
        self.assertEqual(self.post(json.dumps(payload()).encode()), 200)

    def test_busy_decoder_is_bounded_and_snapshot_does_not_wait_for_it(self):
        self.collector.parse_lock.acquire()
        try:
            with patch('inference_telemetry.READ_TIMEOUT', .15):
                self.assertEqual(self.post(b'{}'), 503)
            self.assertEqual(self.collector.snapshot()['processing_busy'], 1)
        finally:
            self.collector.parse_lock.release()
        self.assertEqual(self.post(json.dumps(payload()).encode()), 200)

    def test_unauthorized_data_does_not_enter_size_statistics(self):
        self.assertEqual(self.post(b'{}', authorized=False), 401)
        health = self.collector.snapshot()
        self.assertEqual(health['unauthorized_requests'], 1)
        self.assertTrue(all(value == 0 for key, value in health.items() if key.startswith('size_')))

    def test_native_monitor_bridges_forward_all_public_counters(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('MonitorMac.swift', 'MonitorWpf.cs'):
            source = (root / name).read_text()
            aggregation = source[source.index('"requests","records_scanned"'):] if name.endswith('swift') else source[source.index('"requests", "records_scanned"'):]
            aggregation = aggregation[:aggregation.index('telemetry[key]')]
            fields = set(re.findall(r'"([a-z0-9_]+)"', aggregation))
            self.assertEqual(set(self.collector.snapshot()) - {'enabled'} - fields, set(), name)


if __name__ == '__main__':
    unittest.main()
