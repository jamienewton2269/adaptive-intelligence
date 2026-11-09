"""Unit tests: explanations don't invent device origins."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                      "custom_components" / "adaptive_intelligence"))
from light_explain import explain_light, match_light


class LightExplainTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "light.snug_sofa_led": {"state": "on", "name": "sofa_LED"},
            "input_boolean.jns_lux_include_sofa": {"state": "off"},
            "input_number.jns_lux_rank_sofa": {"state": "8"},
            "input_boolean.jns_lux_manual_hold_all": {"state": "off"},
            "sensor.jns_lighting_effective_lux": {"state": "0"},
            "automation.general_shared_lux_progressive_control": {"state": "on"},
        }

    def test_snug_sofa_excluded(self):
        result = explain_light("light.snug_sofa_led", self.data)
        self.assertEqual(result["causes"][0]["code"], "excluded_from_lux")
        self.assertIn("currently reports on", result["answer"])

    def test_query_by_natural_words(self):
        lights = {"light.snug_sofa_led": {"name": "Snug Sofa LED"},
                  "light.kitchen": {"name": "Kitchen"}}
        self.assertEqual(match_light("Why isn't the Snug Sofa LED turning on automatically tonight?", lights)["entity"],
                         "light.snug_sofa_led")

    def test_unmapped_light_does_not_claim_a_cause(self):
        self.data["light.other"] = {"state": "off", "name": "Other"}
        answer = explain_light("light.other",self.data)
        self.assertEqual(answer["certainty"], "incomplete_evidence")

    def test_global_pause(self):
        self.data["input_boolean.jns_lux_manual_hold_all"]["state"] = "on"
        self.assertIn("global_automatic_pause", [a["code"] for a in explain_light("light.snug_sofa_led",self.data)["causes"]])

    def test_ambiguous_query(self):
        lights = {"light.sofa_1":{"name":"Sofa One"}, "light.sofa_2":{"name":"Sofa Two"}}
        self.assertEqual(match_light("sofa", lights)["status"],"ambiguous")

    def test_living_room_colloquial(self):
        lights = {
            "light.livingroom_pendant": {"name": "Livingroom Pendant"},
            "light.snug_sofa_led": {"name": "sofa_LED"},
            "light.general_hall": {"name": "General Hall Bulb"},
        }
        r = match_light("why is the living room light on", lights)
        self.assertEqual(r, {"status": "found", "entity": "light.livingroom_pendant"})

    def test_room_only_with_two_lights_is_ambiguous(self):
        lights = {
            "light.livingroom_pendant": {"name": "Livingroom Pendant"},
            "light.livingroom_corner": {"name": "Living Room Corner"},
        }
        r = match_light("why is the living room light on?", lights)
        self.assertEqual(r["status"], "ambiguous")
        self.assertEqual(len(r["candidates"]), 2)

    def test_similar_snug_lights_not_conflated(self):
        lights = {
            "light.snug_sofa_led": {"name": "sofa_LED"},
            "light.general_snug_corner": {"name": "General Snug Corner Light"},
        }
        r = match_light("why isn't the Snug Corner lamp on", lights)
        self.assertEqual(r["entity"], "light.general_snug_corner")

    def test_user_defined_alias(self):
        lights = {
            "light.livingroom_pendant": {
                "name": "Livingroom Pendant", "aliases": ["Main lounge light"]
            }
        }
        r = match_light("Why is the main lounge light on?", lights)
        self.assertEqual(r["entity"], "light.livingroom_pendant")

    def test_unknown_is_not_fabricated(self):
        lights = {"light.livingroom_pendant": {"name": "Livingroom Pendant"}}
        self.assertEqual(match_light("Why is the garage roof light on?", lights)["status"], "not_found")


if __name__ == "__main__":
    unittest.main()
