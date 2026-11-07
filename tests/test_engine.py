"""Run from repository root: python -m unittest discover -s tests -v"""
import sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "adaptive_intelligence"))
from engine import classify, validated_lux, make_suggestions


class EngineTests(unittest.TestCase):
    def test_unknown_physical_action_not_manual(self):
        self.assertEqual(classify({"id":"z", "parent_id":None, "user_id":None}, {}, {}), "unknown")

    def test_automation_context(self):
        self.assertEqual(classify({"id":"n", "parent_id":"auto", "user_id":None}, {"auto":object()}, {}), "automation")

    def test_user_context(self):
        self.assertEqual(classify({"id":"u", "parent_id":None, "user_id":"person"}, {}, {}), "user")

    def test_lux_staleness(self):
        now = datetime.now(timezone.utc)
        s = SimpleNamespace(state="9", last_updated=now-timedelta(hours=1))
        self.assertEqual(validated_lux(s,now)[1],"stale")

    def test_lux_valid(self):
        now = datetime.now(timezone.utc)
        s = SimpleNamespace(state="15.5", last_updated=now)
        self.assertEqual(validated_lux(s,now),(15.5,"valid"))

    def test_no_false_suggestion(self):
        now=datetime.now(timezone.utc)
        events=[{"at":(now-timedelta(days=i)).isoformat(), "entity":"light.test",
                 "kind":"light", "classification":"unknown", "old":"off",
                 "new":"on", "override":True} for i in range(20)]
        self.assertEqual(make_suggestions(events, now=now), [])

if __name__ == "__main__":
    unittest.main()
