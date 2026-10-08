import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.bridge.phase_tracking import can_switch_within_turn, dynamic_pipeline, phase_update, proposed_phase, transition_kind


class PhaseTrackingTests(unittest.TestCase):
    def test_compatible_group_is_explicit(self):
        self.assertEqual(transition_kind("gpt-5.6-luna", "gpt-5.6-sol"), "compatible_group")
        phase = proposed_phase("gpt-5.6-luna", "gpt-5.6-sol", "high", "interface")
        self.assertEqual({key: phase[key] for key in ("phase_name", "phase_status", "phase_model", "phase_effort", "phase_transition")}, {
            "phase_name": "execution", "phase_status": "proposed",
            "phase_model": "gpt-5.6-sol", "phase_effort": "high",
            "phase_transition": "compatible_group"})
        self.assertEqual(phase["pipeline_mode"], "plan_and_observation")

    def test_astra_boundary_is_blocked_without_mutating_policy(self):
        self.assertEqual(transition_kind("gpt-5.6-terra", "gpt-6-astra"), "blocked_astra_boundary")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-5.6-terra"), "blocked_astra_boundary")
        row = {"phase_name": "execution", "phase_model": "gpt-5.6-terra", "phase_effort": "medium"}
        self.assertEqual(phase_update(row, "observed", "gpt-5.6-terra", "medium")["phase_status"], "observed")
        self.assertFalse(can_switch_within_turn("gpt-5.6-terra", "gpt-6-astra"))
        self.assertTrue(can_switch_within_turn("gpt-5.6-terra", "gpt-5.6-sol"))

    def test_dynamic_plan_varies_without_claiming_internal_completion(self):
        interface = dynamic_pipeline("interface", steps=["design", "implement", "verify"])
        text = dynamic_pipeline("text", steps=["document"])
        self.assertEqual([item["label"] for item in interface], ["Diseñar", "Implementar", "Validar", "Ejecución en Codex"])
        self.assertEqual([item["label"] for item in text], ["Documentar", "Ejecución en Codex"])
        self.assertEqual(interface[0]["state"], "planned")
        self.assertTrue(all(item["evidence"] == "plan" for item in interface[:-1]))
        active = phase_update({"agent_category": "correction"}, "active")["phase_pipeline"]
        self.assertEqual(active[-1]["state"], "active")
        self.assertEqual(active[-1]["evidence"], "observed")

    def test_unknown_and_same_model_are_conservative(self):
        self.assertEqual(transition_kind(None, "gpt-5.6-terra"), "same_model")
        self.assertEqual(transition_kind("future-model", "gpt-5.6-terra"), "unknown_model")
        self.assertEqual(transition_kind("gpt-6-astra", "gpt-6-astra"), "same_model")


if __name__ == "__main__":
    unittest.main()
