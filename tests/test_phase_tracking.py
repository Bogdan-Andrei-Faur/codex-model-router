import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase_tracking import broad_pipeline, can_switch_within_turn, phase_update, proposed_phase, transition_kind


class PhaseTrackingTests(unittest.TestCase):
    def test_compatible_group_is_explicit(self):
        self.assertEqual(transition_kind("gpt-5.6-luna", "gpt-5.6-sol"), "compatible_group")
        phase = proposed_phase("gpt-5.6-luna", "gpt-5.6-sol", "high")
        self.assertEqual({key: phase[key] for key in ("phase_name", "phase_status", "phase_model", "phase_effort", "phase_transition")}, {
            "phase_name": "execution", "phase_status": "proposed",
            "phase_model": "gpt-5.6-sol", "phase_effort": "high",
            "phase_transition": "compatible_group"})
        self.assertEqual(phase["pipeline_mode"], "observation")

    def test_astra_boundary_is_blocked_without_mutating_policy(self):
        self.assertEqual(transition_kind("gpt-5.6-terra", "gpt-6-astra"), "blocked_astra_boundary")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-5.6-terra"), "blocked_astra_boundary")
        row = {"phase_name": "execution", "phase_model": "gpt-5.6-terra", "phase_effort": "medium"}
        self.assertEqual(phase_update(row, "observed", "gpt-5.6-terra", "medium")["phase_status"], "observed")
        self.assertFalse(can_switch_within_turn("gpt-5.6-terra", "gpt-6-astra"))
        self.assertTrue(can_switch_within_turn("gpt-5.6-terra", "gpt-5.6-sol"))

    def test_broad_pipeline_never_claims_unpublished_internal_boundaries(self):
        proposed = broad_pipeline()
        self.assertEqual([item["id"] for item in proposed], ["preparation", "execution", "review", "closure"])
        self.assertEqual(proposed[0]["state"], "configured")
        self.assertEqual(proposed[2]["state"], "not_observed")
        self.assertEqual(phase_update({}, "active")["phase_pipeline"][1]["state"], "active")

    def test_unknown_and_same_model_are_conservative(self):
        self.assertEqual(transition_kind(None, "gpt-5.6-terra"), "same_model")
        self.assertEqual(transition_kind("future-model", "gpt-5.6-terra"), "unknown_model")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-6-astra"), "same_model")


if __name__ == "__main__":
    unittest.main()
