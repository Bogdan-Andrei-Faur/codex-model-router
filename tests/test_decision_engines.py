import socket
import unittest
import urllib.error
from unittest.mock import patch

from decision_engines import engine_failure, engine_usage, run_jev


class DecisionEngineTests(unittest.TestCase):
    candidates = {
        "simple_low": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low", "description": "Traducción breve"},
        "critical_high": {"model": "gpt-6-astra", "effort": "high", "label": "Astra · high", "description": "Revisión visual"},
    }

    def test_safe_usage_and_failure_classes_do_not_contain_provider_content(self):
        self.assertEqual(engine_usage({"usage": {"input_tokens": 8, "output_tokens": 2, "cached_input_tokens": 1}}),
                         {"engine_input_tokens": 8, "engine_output_tokens": 2, "engine_cached_tokens": 1})
        self.assertEqual(engine_failure(socket.timeout("PRIVATE_SENTINEL")), "timeout")
        self.assertEqual(engine_failure(urllib.error.HTTPError('', 401, '', {}, None)), "authentication")
        self.assertEqual(engine_failure(urllib.error.HTTPError('', 403, '', {}, None)), "forbidden")

    @patch("decision_engines.jev_key", return_value="synthetic-key")
    @patch("decision_engines._post_json")
    def test_jev_uses_vercel_evaluate_with_virtual_model(self, post, key):
        post.return_value = {"answers": {"strategy": {"choice": "reassess"},
                                          "route": {"choice": "simple_low", "confidence": 0.9}},
                             "usage": {"inputTokens": 12, "outputTokens": 2}}
        result = run_jev({"jev": {"connection": "vercel"}}, "", {"task": "PRIVATE_SENTINEL"}, self.candidates)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine_model"], "vmc/jev")
        self.assertEqual((result["engine_input_tokens"], result["engine_output_tokens"]), (12, 2))
        self.assertEqual(post.call_args.args[0], "https://ai-gateway.vercel.sh/v1/evaluate")
        self.assertEqual(post.call_args.args[1]["model"], "vmc/jev")
        self.assertEqual(post.call_args.args[2], {"Authorization": "Bearer synthetic-key"})
        self.assertEqual(result["continuity_strategy"], "reassess")
        self.assertIn("strategy", post.call_args.args[1]["questions"])
        key.assert_called_once_with("", "vercel")
        self.assertNotIn("PRIVATE_SENTINEL", str(result))

    @patch("decision_engines.jev_key", return_value="synthetic-key")
    @patch("decision_engines._post_json")
    def test_jev_records_an_explicit_continuation_strategy(self, post, key):
        post.return_value = {"answers": {"strategy": {"choice": "continue"}, "route": {"choice": "simple_low"}}}
        result = run_jev({}, "", {"task": "PRIVATE_SENTINEL", "previous_model": "gpt-6-astra", "previous_effort": "high"}, self.candidates)
        self.assertEqual(result["continuity_strategy"], "continue")
        self.assertIn("continue", post.call_args.args[1]["questions"]["strategy"]["criteria"])

    @patch("decision_engines.jev_key", return_value="synthetic-key")
    @patch("decision_engines._post_json")
    def test_jev_connection_ignores_stale_other_provider_endpoint_and_model(self, post, key):
        post.return_value = {"answers": {"route": {"choice": "simple_low"}}}
        result = run_jev({"jev": {"connection": "vercel", "endpoint": "https://api.typesafe.ai/v1/systemone",
                                  "model": "jev-latest"}}, "", {"task": "PRIVATE_SENTINEL"}, self.candidates)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine_model"], "vmc/jev")
        self.assertEqual(post.call_args.args[0], "https://ai-gateway.vercel.sh/v1/evaluate")
        self.assertEqual(post.call_args.args[1]["model"], "vmc/jev")

    @patch("decision_engines.jev_key", return_value="synthetic-key")
    @patch("decision_engines._post_json")
    def test_jev_keeps_direct_typesafe_as_default(self, post, key):
        post.return_value = {"answers": {"route": {"choice": "critical_high"}}}
        result = run_jev({}, "", {"task": "PRIVATE_SENTINEL"}, self.candidates)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine_model"], "jev-latest")
        self.assertEqual(post.call_args.args[0], "https://api.typesafe.ai/v1/systemone")
        key.assert_called_once_with("", "typesafe")
