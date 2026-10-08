import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from codex_model_router.routing.decision_engines import engine_usage, token_count
import codex_model_router.routing.candidate_policy as cp


class StrictEngineCounterTests(unittest.TestCase):
    def test_unknown_values_are_not_rounded_coerced_or_reported_as_zero(self):
        class Coercible:
            def __int__(self):
                raise AssertionError('must not coerce arbitrary provider objects')
        invalid = (True, False, None, 1.2, -1, -0.1, float('inf'), float('-inf'), float('nan'),
                   1_000_000_001, '', '-0', '-1', '1.0', '1e2', '1_000', '1 0',
                   '１２', '١٢', '²', '0'*11, '9'*5000, [], {}, Coercible())
        for value in invalid:
            with self.subTest(value_type=type(value).__name__):
                self.assertIsNone(token_count(value))
        for value, expected in ((0, 0), (42.0, 42), (' +42 ', 42), ('00042', 42),
                                ('\t1000000000\n', 1_000_000_000)):
            self.assertEqual(token_count(value), expected)

    def test_invalid_usage_counters_do_not_drop_valid_reported_provider_cost(self):
        result = engine_usage({'usage': {'input_tokens': True, 'output_tokens': 1.2,
                                        'cached_tokens': float('inf')},
                               'providerMetadata': {'gateway': {'cost': '0.001'}}})
        self.assertEqual(result, {'engine_provider_cost_usd': .001})
        self.assertEqual(engine_usage({'usage': {'inputTokens': '8', 'outputTokens': 2.0,
                                                'cached_input_tokens': '0'}}),
                         {'engine_input_tokens': 8, 'engine_output_tokens': 2, 'engine_cached_tokens': 0})

    def test_integral_numeric_values_are_not_service_integration_or_risk(self):
        for text in ('Repara la función acotada: valida un float integral.',
                     'Repara una función pequeña de números integrales.',
                     'Fix a bounded parser for integral floats.'):
            with self.subTest(text=text):
                self.assertEqual(cp.profile(text)['work_class'], 'bounded')
        for text in ('Integra la función acotada con los servicios externos.',
                     'Implementa la integración entre servicios.'):
            self.assertEqual(cp.profile(text)['work_class'], 'engineering')
            self.assertEqual(cp.profile(text)['preferred_effort'], 'high')
        self.assertEqual(cp.profile('Repara un float integral en una función acotada.',
                                   contract={'risk_active': True})['work_class'], 'critical')


if __name__ == '__main__':
    unittest.main()
