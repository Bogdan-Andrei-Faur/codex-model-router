import copy
import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import codex_model_router.routing.candidate_policy as cp
from codex_model_router.telemetry.inference_telemetry import bounded_number, safe_records
from codex_model_router.telemetry.inference_attribution import attribute
from tests.test_inference_telemetry import payload
from tests import test_phase_control as phases


class PhaseEffortTests(unittest.TestCase):
    setUp = phases.PhaseControlTests.setUp
    enroll = phases.PhaseControlTests.enroll
    begin = phases.PhaseControlTests.begin
    checkpoint = phases.PhaseControlTests.checkpoint
    status = phases.PhaseControlTests.status
    def start_astra(self, minimum='high'):
        self.begin(floor='critical', model='gpt-6-astra')
        self.router.threads['t'].update(effort='high', accepted_effort='high')
        self.router.phases.turns['t']['min_effort'] = minimum

    def test_inherited_floor_does_not_restore_xhigh(self):
        for complexity in ('normal', 'complex'):
            with self.subTest(complexity=complexity):
                self.start_astra()
                self.checkpoint(arguments={'phase': 'implement', 'complexity': complexity})
                reply, = self.router.drain_outbound()
                self.assertEqual(self.status(reply), 'unchanged')
                self.assertEqual(self.router.threads['t']['accepted_model'], 'gpt-6-astra')

    def test_actual_critical_phase_still_raises_effort(self):
        self.start_astra()
        self.checkpoint(arguments={'phase': 'verify', 'complexity': 'critical'})
        request, = self.router.drain_outbound()
        self.assertEqual(request['params']['effort'], 'xhigh')

    def test_explicit_minimum_wins_over_remaining_complexity(self):
        self.start_astra('xhigh')
        self.checkpoint(arguments={'phase': 'implement', 'complexity': 'normal'})
        request, = self.router.drain_outbound()
        self.assertEqual(request['params']['effort'], 'xhigh')

    def test_unsupported_effort_is_preserved(self):
        self.start_astra()
        self.router.catalog['gpt-6-astra'] = {'xhigh'}
        self.checkpoint(arguments={'phase': 'implement', 'complexity': 'normal'})
        reply, = self.router.drain_outbound()
        self.assertEqual(self.status(reply), 'preserved')


class MetricsRemediationTests(unittest.TestCase):
    def test_legacy_uncertainty_stays_uncertain_across_turns(self):
        a = cp.profile('Adelante', context={'work_floor': 'critical'})
        for _ in range(3):
            self.assertEqual((a['risk_active'], a['legacy_uncertain'], a['risk_basis'], a['work_class']),
                             (False, True, 'legacy_uncertain', 'critical'))
            a = cp.profile('Solo queda documentar', contract=cp.next_contract({}, a))
        self.assertEqual(cp.profile('Nueva tarea: traduce hola', contract=cp.next_contract({}, a))['risk_basis'], 'none')

    def test_real_and_old_risk_remain_conservative(self):
        a = cp.profile('Investiga pérdida de datos')
        self.assertEqual(a['risk_basis'], 'current')
        self.assertEqual(cp.profile('Solo queda documentar', contract=cp.next_contract({}, a))['risk_basis'], 'inherited')
        self.assertEqual(cp.profile('Adelante', contract={'risk_active': True})['work_class'], 'critical')

    def test_counter_rejects_fraction_and_boolean_without_rejecting_integral_float(self):
        for value in (True, False, 1.5, '1.5', '-0', '１２', '9'*5000, [], None, float('nan')):
            self.assertIsNone(bounded_number(value, 10**9, integer=True))
        for value in (3, 3.0, ' +3 '):
            self.assertEqual(bounded_number(value, 10**9, integer=True), 3)

    def event(self, **attrs):
        data = payload()
        log = data['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        log['timeUnixNano'] = '1700000000000000001'
        for key, value in attrs.items():
            log['attributes'] = [a for a in log['attributes'] if a['key'] != key]
            log['attributes'].append({'key': key, 'value': {'stringValue': value}})
        return data

    def test_duplicate_hash_uses_complete_safe_event(self):
        baseline = self.event()
        record, = safe_records(baseline)
        reordered = copy.deepcopy(baseline)
        log = reordered['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        log['attributes'].reverse(); log['body'] = {'stringValue': 'different private text'}
        self.assertEqual(record['event_id'], list(safe_records(reordered))[0]['event_id'])
        for attrs in ({'event.name': 'codex.api_request'}, {'model_reasoning_effort': 'high'}, {'output_token_count': '9'}):
            self.assertNotEqual(record['event_id'], list(safe_records(self.event(**attrs)))[0]['event_id'])

    def test_camelcase_identities_and_conflicts(self):
        record, = safe_records(self.event(turnId='turn_12345678', responseId='resp_12345678'))
        self.assertEqual(record['turn_id'], 'turn_12345678')
        self.assertEqual(record['response_id'], 'resp_12345678')
        self.assertEqual(list(safe_records(self.event(threadId='other_12345678'))), [])

    def test_malformed_timestamp_is_not_identity(self):
        data = payload(); data['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]['timeUnixNano'] = '9'*5000
        record, = safe_records(data)
        self.assertNotIn('timestamp', record); self.assertNotIn('event_id', record)

    def test_native_zero_event_time_uses_observed_time_without_duplicate_collapse(self):
        data = self.event()
        log = data['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        log.update(timeUnixNano='0', observedTimeUnixNano='1700000000000000001')
        first, = safe_records(data)
        self.assertEqual(first['timestamp_source'], 'observed')
        self.assertGreater(first['timestamp'], 0)
        self.assertEqual(first, list(safe_records(data))[0])
        log['observedTimeUnixNano'] = '1700000000000000002'
        second, = safe_records(data)
        self.assertNotEqual(first['event_id'], second['event_id'])
        log['timeUnixNano'] = '1600000000000000001'
        event, = safe_records(data)
        self.assertEqual(event['timestamp_source'], 'event')
        self.assertLess(event['timestamp'], second['timestamp'])

    def test_observation_time_cannot_confirm_inference_after_phase_change(self):
        threads = {'thread': dict(turn_id='turn', phase_status='active', phase_accepted_at=10,
                                  phase_model='gpt-6.1-sol', phase_effort='high')}
        record = dict(thread_id='thread', turn_id='turn', model='gpt-6.1-sol', effort='high', timestamp=20)
        self.assertTrue(attribute(dict(record, timestamp_source='event'), threads, 30)[1])
        self.assertFalse(attribute(dict(record, timestamp_source='observed'), threads, 30)[1])


if __name__ == '__main__':
    unittest.main()
