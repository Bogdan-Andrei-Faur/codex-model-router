import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase_tracking import phase_update, proposed_phase, transition_kind


class PhaseTrackingTests(unittest.TestCase):
    def test_compatible_group_is_explicit(self):
        self.assertEqual(transition_kind("gpt-5.6-luna", "gpt-5.6-sol"), "compatible_group")
        self.assertEqual(proposed_phase("gpt-5.6-luna", "gpt-5.6-sol", "high"), {
            "phase_name": "execution", "phase_status": "proposed",
            "phase_model": "gpt-5.6-sol", "phase_effort": "high",
            "phase_transition": "compatible_group"})

    def test_astra_boundary_is_blocked_without_mutating_policy(self):
        self.assertEqual(transition_kind("gpt-5.6-terra", "gpt-6-astra"), "blocked_astra_boundary")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-5.6-terra"), "blocked_astra_boundary")
        row = {"phase_name": "execution", "phase_model": "gpt-5.6-terra", "phase_effort": "medium"}
        self.assertEqual(phase_update(row, "observed", "gpt-5.6-terra", "medium")["phase_status"], "observed")

    def test_unknown_and_same_model_are_conservative(self):
        self.assertEqual(transition_kind(None, "gpt-5.6-terra"), "same_model")
        self.assertEqual(transition_kind("future-model", "gpt-5.6-terra"), "unknown_model")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-6-astra"), "same_model")


if __name__ == "__main__":
    unittest.main()
