import socket
import unittest
import urllib.error
from unittest.mock import patch

from decision_engines import candidate_routes, engine_failure, engine_usage, run_jev
from routing import DEFAULT_ROUTES, EFFORTS, select_route_details


class DecisionEngineTests(unittest.TestCase):
    candidates = {
        "simple_low": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low", "description": "Traducción breve"},
        "critical_high": {"model": "gpt-6-astra", "effort": "high", "label": "Astra · high", "description": "Revisión visual"},
    }

    def test_candidates_require_evidence_for_maximum_and_keep_real_quality_floors(self):
        catalog = {route["model"]: set(EFFORTS) for route in DEFAULT_ROUTES.values()}
        cases = [
            ("Parece que ahora si esta funcionando", "critical", "max", False, {"simple", "normal"}),
            ("Ok, perfecto", "critical", "max", False, {"simple", "normal"}),
            ("Adelante, impleméntalo", "critical", "max", False, {"critical"}),
            ("Investiga una condición de carrera entre servicios", None, None, False, {"complex", "critical"}),
            ("Audita de forma exhaustiva la autenticación", None, None, True, {"critical"}),
            ("Sigue fallando", "critical", "xhigh", True, {"critical"}),
            ("Sigue fallando", "critical", "high", False, {"critical"}),
            ("Tengo una duda sobre esto", "critical", "max", False, {"simple", "normal", "complex", "critical"}),
        ]
        for prompt, previous, effort, allow_max, tiers in cases:
            with self.subTest(prompt=prompt, effort=effort):
                _, policy = select_route_details(prompt, DEFAULT_ROUTES, previous, effort)
                choices = candidate_routes(DEFAULT_ROUTES, catalog, policy)
                self.assertEqual("critical_max" in choices, allow_max)
                self.assertEqual({item["tier"] for item in choices.values()}, tiers)
        choices = candidate_routes(DEFAULT_ROUTES, catalog, {"max_effort_allowed": True})
        descriptions = [choices["critical_" + effort]["description"] for effort in ("high", "xhigh", "max")]
        self.assertEqual(len(set(descriptions)), 3)

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
