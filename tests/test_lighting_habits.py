"""Habits v1: conservative learning, no unverified attribution."""
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                      "custom_components" / "adaptive_intelligence"))
from lighting_habits import summarise_lighting_habits


class LightingHabitTests(unittest.TestCase):
    def setUp(self):
        self.z = ZoneInfo("Europe/London")
        self.now = datetime(2026, 11, 13, 20, tzinfo=self.z)

    def make(self, day, hour=18, minute=35, classification="user", old="off",
             new="on", entity="light.snug_sofa_led", quality=None):
        at = datetime(2026, 10, day, hour, minute, tzinfo=self.z)
        e = {"at": at.isoformat(), "kind": "light", "entity": entity,
             "old": old, "new": new, "classification": classification}
        if quality: e["lux_quality"] = quality
        return e

    def test_automations_cannot_create_manual_habits(self):
        events = [self.make(d, classification="automation") for d in (2, 5, 7, 8, 9, 12, 13, 14)]
        x = summarise_lighting_habits(events, now=self.now)
        self.assertEqual(x["candidates"], [])
        self.assertEqual(x["counts"]["verified_manual"], 0)

    def test_attribute_updates_ignored(self):
        events = [self.make(1,old="on",new="on") for _ in range(30)]
        self.assertEqual(summarise_lighting_habits(events,now=self.now)["counts"]["on_off_transitions"],0)

    def test_two_days_is_early_only(self):
        x = summarise_lighting_habits([self.make(1),self.make(2)],now=self.now)
        self.assertEqual(len(x["early_patterns"]),1)
        self.assertFalse(x["candidates"])

    def test_minimum_days_and_span(self):
        # Use multiple dates but keep same weekday/weekend class.
        days = [1, 2, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16]
        events = [self.make(d) for d in days]
        x = summarise_lighting_habits(events, now=self.now, min_days=5,min_span_days=10)
        self.assertTrue(x["candidates"])
        self.assertEqual(x["candidates"][0]["permission"],"suggest_only")

    def test_unknown_not_manual(self):
        x = summarise_lighting_habits([self.make(d,classification="unknown") for d in range(1,14)],now=self.now)
        self.assertFalse(x["candidates"])
        self.assertEqual(x["counts"]["unattributed"],13)

    def test_invalid_lux_excluded(self):
        x = summarise_lighting_habits([self.make(d,quality="stale") for d in range(1,9)],now=self.now)
        self.assertEqual(x["counts"]["verified_manual"],0)
        self.assertEqual(x["counts"]["excluded_quality"],8)

    def test_no_naive_timestamps(self):
        event=self.make(2);event["at"]="2026-10-02T18:35:00"
        self.assertEqual(summarise_lighting_habits([event],now=self.now)["counts"]["on_off_transitions"],0)

    def test_off_is_separate_from_on(self):
        events=[self.make(2,old="on",new="off"),self.make(5,old="on",new="off")]
        x=summarise_lighting_habits(events,now=self.now)
        self.assertTrue(all(e["action"]=="off" for e in x["early_patterns"]))

    def test_weekend_separate_from_weekday(self):
        # Oct 3-4 2026 are weekend, Oct 5 is weekday.
        x=summarise_lighting_habits([self.make(3),self.make(4),self.make(5)],now=self.now)
        self.assertEqual(len(x["early_patterns"]),1)
        self.assertEqual(x["early_patterns"][0]["day_class"],"weekend")

if __name__=="__main__":
    unittest.main()
