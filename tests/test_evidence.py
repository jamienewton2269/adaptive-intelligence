"""Pure physical-input evidence tests."""
from datetime import datetime, timezone
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "adaptive_intelligence"))
from evidence import physical_input, classify_quality


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.at = datetime(2026, 11, 7, 20, tzinfo=timezone.utc)

    def test_zigbee_action_candidate(self):
        data = physical_input("sensor.button_action", "single", "double", self.at)
        self.assertEqual(data["classification"], "physical_candidate")
        self.assertFalse(data["override"])

    def test_event_candidate(self):
        data = physical_input("event.button", "2026-11-06", "2026-11-07", self.at)
        self.assertEqual(data["signal_type"], "event_entity")

    def test_ordinary_sensor_not_candidate(self):
        self.assertIsNone(physical_input("sensor.room_temperature", "18", "19", self.at))

    def test_unavailable_not_candidate(self):
        self.assertIsNone(physical_input("sensor.button_action", "single", "unavailable", self.at))

    def test_lux_fault_classification(self):
        self.assertEqual(classify_quality({"kind":"light","lux_quality":"stale"}), "lux_unreliable")


if __name__ == "__main__":
    unittest.main()
