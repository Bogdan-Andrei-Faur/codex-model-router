import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usage_state import AccountUsage, context_window
from router import Router
from monitor_state import MonitorState
from routing import DEFAULT_ROUTES


def bucket(used=24, duration=10080, reset=500):
    return {'primary': {'usedPercent': used, 'windowDurationMins': duration, 'resetsAt': reset}}


class UsageStateTests(unittest.TestCase):
    def test_context_uses_last_not_lifetime_or_double_counted_cache(self):
        result = context_window({'modelContextWindow': 1000,
            'total': {'totalTokens': 999999},
            'last': {'totalTokens': 370, 'inputTokens': 300, 'cachedInputTokens': 280,
                     'outputTokens': 70, 'reasoningOutputTokens': 60}}, now=10)
        self.assertEqual(result, {'used_tokens': 370, 'capacity_tokens': 1000, 'used_percent': 37, 'updated': 10})

    def test_context_missing_invalid_and_full_are_distinct(self):
        for capacity in (None, 0, -1, '100', True, float('nan'), float('inf')):
            self.assertNotIn('used_percent', context_window({'modelContextWindow': capacity, 'last': {'totalTokens': 0}}))
        for used in (None, -1, '1', True, float('inf')):
            self.assertNotIn('used_percent', context_window({'modelContextWindow': 10, 'last': {'totalTokens': used}}))
        for used, expected in ((0, 0), (10, 100), (11, 100)):
            self.assertEqual(context_window({'modelContextWindow': 10, 'last': {'totalTokens': used}})['used_percent'], expected)

    def test_quota_prefers_buckets_deduplicates_legacy_and_omits_private_data(self):
        usage = AccountUsage()
        usage.update({'rateLimits': bucket(99), 'accountId': 'PRIVATE',
                      'rateLimitsByLimitId': {'codex': bucket(), 'extra': bucket(60)},
                      'ordinaryUsageAllowed': False}, 10, replace=True)
        self.assertEqual(usage.snapshot['remaining_percent'], 40)
        self.assertEqual(len(usage.snapshot['windows']), 2)
        self.assertEqual(usage.snapshot['valid_until'], 190)
        self.assertNotIn('PRIVATE', json.dumps(usage.snapshot))
        # A sparse notification updates one bucket without refreshing other windows.
        usage.consume({'method': 'account/rateLimits/updated', 'params': {'rateLimits': {'limitId': 'extra', **bucket(20)}}}, now=100)
        self.assertEqual(usage.snapshot['remaining_percent'], 76)
        self.assertEqual(usage.snapshot['valid_until'], 190)
        self.assertIs(usage.snapshot['ordinary_usage_allowed'], False)

    def test_missing_quota_is_not_zero_and_reset_expires_sample(self):
        usage = AccountUsage()
        for invalid in (None, True, -10, '24', float('nan')):
            usage.update({'rateLimits': bucket(invalid)}, 10, replace=True)
            self.assertNotIn('remaining_percent', usage.snapshot)
        usage.update({'rateLimits': {'primary': None, 'secondary': bucket(100, reset=20)['primary']}}, 10, replace=True)
        self.assertEqual(usage.snapshot['remaining_percent'], 0)
        self.assertEqual(usage.snapshot['valid_until'], 20)
        usage.update({'rateLimits': bucket(0)}, 10, replace=True)
        self.assertEqual(usage.snapshot['remaining_percent'], 100)

    def test_poll_is_read_only_bounded_and_late_replies_are_suppressed(self):
        usage = AccountUsage()
        self.assertIsNone(usage.poll(False, now=10))
        request = usage.poll(True, now=10)
        self.assertEqual(request['method'], 'account/rateLimits/read')
        self.assertIsNone(usage.poll(True, now=69))
        newer = usage.poll(True, now=70)
        self.assertTrue(usage.consume({'id': request['id'], 'result': {'rateLimits': bucket()}}, now=71))
        self.assertEqual(usage.snapshot, {})
        self.assertTrue(usage.consume({'id': newer['id'], 'result': {'rateLimits': bucket()}}, now=72))
        self.assertEqual(usage.snapshot['remaining_percent'], 76)
        self.assertFalse(usage.consume({'id': 'desktop-rpc', 'result': {'rateLimits': bucket()}}, now=72))

    def test_account_switch_clears_data_and_discards_old_inflight_reply(self):
        usage = AccountUsage()
        old = usage.poll(True, now=10)
        usage.update({'rateLimits': bucket()}, 10, replace=True)
        self.assertFalse(usage.consume({'method': 'account/updated', 'params': {'authMode': None}}, now=11))
        usage.consume({'id': old['id'], 'result': {'rateLimits': bucket()}}, now=12)
        self.assertEqual(usage.snapshot, {'updated': 11})
        self.assertIsNotNone(usage.poll(True, now=12))

    def test_router_keeps_notifications_transparent_and_context_per_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'
            config.write_text(json.dumps({'routes': DEFAULT_ROUTES}))
            router = Router(config, Path(tmp) / 'state')
            router.threads = {'parent': {'model': 'gpt-6.1-sol'}, 'child': {'parent': 'parent'}}
            notification = {'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'parent',
                'tokenUsage': {'last': {'totalTokens': 40}, 'modelContextWindow': 100}}}
            self.assertTrue(router.server_line(json.dumps(notification)))
            self.assertEqual(router.threads['parent']['context_window']['used_percent'], 40)
            self.assertNotIn('context_window', router.threads['child'])
            for method, params in [
                ('item/started', {'item': {'type': 'contextCompaction'}}),
                ('item/completed', {'item': {'type': 'contextCompaction'}}),
                ('thread/compacted', {}),
                ('thread/settings/updated', {'threadSettings': {'model': 'gpt-6-astra'}}),
            ]:
                router.server_line(json.dumps(notification))
                router.server_line(json.dumps({'method': method, 'params': {'threadId': 'parent', **params}}))
                self.assertNotIn('context_window', router.threads['parent'])
            router.handshake_complete = True
            router.client_name = 'codex_desktop'
            request = next(r for r in router.drain_outbound() if r['method'] == 'account/rateLimits/read')
            self.assertFalse(router.server_line(json.dumps({'id': request['id'], 'result': {'rateLimits': bucket()}})))
            router.log({'event': 'test'})
            snapshot = json.loads(next((Path(tmp) / 'state').glob('status-*.json')).read_text())
            self.assertEqual(snapshot['account_usage']['remaining_percent'], 76)

    def test_monitor_uses_latest_live_account_snapshot_without_summing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'state').mkdir(); (root / 'VERSION').write_text('0.6.0')
            for index, updated in enumerate((10, 30, 20)):
                data = {'pid': os.getpid(), 'heartbeat': 100, 'threads': {},
                        'account_usage': {'updated': updated, 'remaining_percent': updated}}
                (root / 'state' / ('status-%s.json' % index)).write_text(json.dumps(data))
            with patch('monitor_state.time.time', return_value=100):
                self.assertEqual(MonitorState(root).payload()['accountUsage']['remaining_percent'], 30)
            with patch('monitor_state.time.time', return_value=113):
                self.assertEqual(MonitorState(root).payload()['accountUsage'], {})


if __name__ == '__main__':
    unittest.main()
