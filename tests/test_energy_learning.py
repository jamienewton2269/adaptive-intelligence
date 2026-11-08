"""Run python -m unittest discover -s tests -v."""
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                      "custom_components" / "adaptive_intelligence"))
from energy_learning import PowerSample, extract_cycles, cycle_similarity, rank_start_times


class EnergyLearningTests(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)

    def test_unknown_meter_no_samples(self):
        self.assertEqual(extract_cycles([]), [])

    def test_detect_dedicated_cycle(self):
        s = [PowerSample(self.t+timedelta(minutes=i),
                         0 if i in (0, 1, 12, 13, 14, 15, 16, 17) else 900)
             for i in range(18)]
        cycles = extract_cycles(s)
        self.assertEqual(len(cycles), 1)
        self.assertGreater(cycles[0].energy_kwh, 0.1)
        self.assertLess(cycles[0].energy_kwh, 0.3)

    def test_gap_rejected(self):
        s = [PowerSample(self.t, 900),
             PowerSample(self.t+timedelta(minutes=20), 900)]
        self.assertEqual(extract_cycles(s), [])

    def test_similarity_is_not_certainty(self):
        s = [PowerSample(self.t+timedelta(minutes=i), 200) for i in range(10)]
        c = extract_cycles(s)[0]
        self.assertEqual(cycle_similarity(c, c), 1.0)

    def test_rank_lower_carbon(self):
        s = [{"start": self.t+timedelta(minutes=30*i),
              "end": self.t+timedelta(minutes=30*(i+1)),
              "carbon_g_kwh": v, "forecast_valid": True}
             for i,v in enumerate([300,300,100,90])]
        options = rank_start_times([0.5,0.5],s,earliest=self.t,
                                   deadline=self.t+timedelta(hours=2))
        self.assertEqual(options[0]["start"],s[2]["start"].isoformat())
        self.assertEqual(options[0]["action"],"suggest_only")

    def test_stale_forecast_not_eligible(self):
        s = [{"start":self.t, "end":self.t+timedelta(minutes=30),
              "carbon_g_kwh":30, "forecast_valid":False}]
        self.assertEqual(rank_start_times([0.2],s,earliest=self.t,deadline=s[0]["end"]), [])


if __name__ == "__main__":
    unittest.main()
