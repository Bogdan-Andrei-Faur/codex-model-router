import socket
import unittest
from unittest.mock import patch

from decision_engines import engine_failure, engine_usage, parse_provider_choice, run_provider


class ProviderResponseTests(unittest.TestCase):
    candidates = {
        "simple_low": {"model": "gpt-5.6-luna", "effort": "low", "label": "Luna · low", "description": "Traducción breve"},
        "critical_high": {"model": "gpt-6-astra", "effort": "high", "label": "Astra · high", "description": "Revisión visual"},
    }

    def test_accepts_explicit_single_choice_only(self):
        for response in ['simple_low', '{"route":"simple_low"}', '```json\n{"route":"simple_low"}\n```']:
            with self.subTest(response=response):
                self.assertEqual(parse_provider_choice(response, self.candidates), "simple_low")

    def test_thinking_alternatives_do_not_override_final_selection(self):
        for response in ['Consider simple_low or critical_high.</think>{"route":"critical_high"}',
                         '<think>simple_low?</think>```json\n{"route":"critical_high"}\n```']:
            self.assertEqual(parse_provider_choice(response, self.candidates), "critical_high")
        self.assertIsNone(parse_provider_choice('simple_low</think>', self.candidates))
        self.assertIsNone(parse_provider_choice('reasoning</think>simple_low or critical_high', self.candidates))

    def test_rejects_ambiguous_prose_unknown_routes_and_duplicate_json_keys(self):
        for response in ['Podría ser simple_low o critical_high.', 'No elijas simple_low.',
                         '{"route":"unknown"}', '{"route":["simple_low","critical_high"]}',
                         '{"route":"simple_low","alternative":"critical_high"}',
                         '{"route":"simple_low","route":"critical_high"}', '{}', '', None]:
            with self.subTest(response=response):
                self.assertIsNone(parse_provider_choice(response, self.candidates))

    @patch("decision_engines._post_json")
    def test_provider_reads_json_selection_and_does_not_return_response_content(self, post):
        post.return_value = {"message": {"content": '{"route":"critical_high"}'}, "prompt_eval_count": 12, "eval_count": 3}
        result = run_provider({}, "", {"task": "PRIVATE_SENTINEL"}, self.candidates)
        self.assertEqual(result["route"]["model"], "gpt-6-astra")
        self.assertEqual((result["engine_input_tokens"], result["engine_output_tokens"]), (12, 3))
        self.assertNotIn("PRIVATE_SENTINEL", str(result))
        messages = post.call_args.args[1]["messages"]
        self.assertNotIn("PRIVATE_SENTINEL", messages[0]["content"])
        self.assertIn("Revisión visual", messages[0]["content"])

    def test_safe_usage_and_failure_classes_do_not_contain_provider_content(self):
        self.assertEqual(engine_usage({"usage": {"input_tokens": 8, "output_tokens": 2, "cached_input_tokens": 1}}),
                         {"engine_input_tokens": 8, "engine_output_tokens": 2, "engine_cached_tokens": 1})
        self.assertEqual(engine_failure(socket.timeout("PRIVATE_SENTINEL")), "timeout")
