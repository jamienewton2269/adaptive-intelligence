"""Zigbee action observations must never imply a light mapping."""
import sys,unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"custom_components"/"adaptive_intelligence"))
from zigbee_actions import parse_zigbee_action


class ZigbeeInputTests(unittest.TestCase):
    def setUp(self):self.at=datetime(2026,11,17,12,tzinfo=timezone.utc)
    def test_valid(self):
        x=parse_zigbee_action("zigbee2mqtt/Bedroom Button/action","single",self.at)
        self.assertEqual(x["signal"],"single")
        self.assertFalse(x["verified_target"])
        self.assertEqual(x["classification"],"physical_candidate")
    def test_wrong_topic(self):
        self.assertIsNone(parse_zigbee_action("zigbee2mqtt/Bedroom Button", "single",self.at))
    def test_json_payload_rejected(self):
        self.assertIsNone(parse_zigbee_action("zigbee2mqtt/Button/action",'{"action":"single"}',self.at))
    def test_payload_invalid(self):
        self.assertIsNone(parse_zigbee_action("zigbee2mqtt/Button/action",b"\xff",self.at))
    def test_bridge_not_a_button(self):
        self.assertIsNone(parse_zigbee_action("zigbee2mqtt/bridge/action","single",self.at))


if __name__=="__main__":unittest.main()
