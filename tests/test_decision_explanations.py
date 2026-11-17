"""Regression tests for conservative household lighting explanations."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components" / "adaptive_intelligence" / "decision_explanations.py"
spec = importlib.util.spec_from_file_location("decision_explanations", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DecisionExplanationsTests(unittest.TestCase):
    def test_unknown_never_claims_cause(self):
        event = {"kind": "light", "entity": "light.test", "old": "off", "new": "on"}
        result = module.describe_transition(event)
        self.assertEqual(result["source"], "Cause not yet confirmed")
        self.assertIn("No verified", result["reason"])
        self.assertTrue(result["read_only"])

    def test_automation_context_not_proof(self):
        event = {"kind": "light", "old": "on", "new": "off", "classification": "automation",
                 "lux": 38, "lux_quality": "valid"}
        result = module.describe_transition(event)
        self.assertIn("trace not verified", result["source"])
        self.assertIn("38 lux", result["outdoor_brightness"])

    def test_brightness(self):
        event = {"kind": "light", "old": "on", "new": "on",
                 "old_brightness": 100, "new_brightness": 150}
        self.assertEqual(module.describe_transition(event)["change"], "Changed brightness")

    def test_noop(self):
        self.assertIsNone(module.describe_transition({"kind": "light", "old": "on", "new": "on"}))

    def test_manual_override(self):
        event = {"kind": "light", "old": "off", "new": "on",
                 "classification": "user", "override": True}
        self.assertIn("reversed", module.describe_transition(event)["manual_preference"])

    def test_recent_order(self):
        events = [{"kind": "light", "entity": str(i), "old": "off", "new": "on"}
                  for i in range(3)]
        self.assertEqual([x["entity"] for x in module.recent_explanations(events, 2)],
                         ["2", "1"])


if __name__ == "__main__":
    unittest.main()
