"""Regression checks: genuine lighting transitions survive telemetry floods."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       "custom_components" / "adaptive_intelligence"))
from observation_store import compact_observations, is_useful_event


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,17,13,tzinfo=timezone.utc)

    def event(self,mins,kind="light",old="off",new="on",**kwargs):
        return {"at":(self.now-timedelta(minutes=mins)).isoformat(),
                "kind":kind,"entity":"light.snug_sofa_led",
                "old":old,"new":new,**kwargs}

    def test_flood_does_not_evict_real_transition(self):
        real=self.event(30)
        flood=[self.event(20-i/100,old="on",new="on") for i in range(6000)]
        got=compact_observations([real,*flood],limit=100,now=self.now)
        self.assertEqual(got,[real])

    def test_physical_candidate_preserved_unverified(self):
        physical=self.event(1,kind="physical_input",signal="single")
        self.assertEqual(compact_observations([physical],now=self.now),[physical])

    def test_climate_target_only(self):
        changed=self.event(2,kind="climate",old="heat",new="heat",
                           previous_target={"temperature":18},
                           new_target={"temperature":21})
        unchanged=self.event(3,kind="climate",old="heat",new="heat",
                             previous_target={"temperature":21},
                             new_target={"temperature":21})
        self.assertEqual(compact_observations([unchanged,changed],now=self.now),[changed])

    def test_bad_old_new_not_transition(self):
        self.assertFalse(is_useful_event(self.event(1,old="unavailable",new="on")))

    def test_old_and_future_rejected(self):
        self.assertEqual(compact_observations([self.event(130000),self.event(-20)],now=self.now),[])

    def test_limit_applies_only_to_useful(self):
        events=[self.event(i) for i in range(9,-1,-1)]
        self.assertEqual(compact_observations(events,limit=3,now=self.now),events[-3:])


if __name__=="__main__":
    unittest.main()
