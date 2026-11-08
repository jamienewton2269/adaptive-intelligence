"""Appliance energy fingerprinting and carbon-aware scheduling primitives.

JNSystems · In memory of Becki and Dad.

Pure, dependency-free analysis. No Home Assistant, Zigbee or switching APIs.
Unknown devices are never assigned an appliance identity automatically.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from statistics import median


@dataclass(frozen=True)
class PowerSample:
    timestamp: datetime
    watts: float


@dataclass(frozen=True)
class Cycle:
    started_at: datetime
    ended_at: datetime
    duration_minutes: float
    energy_kwh: float
    peak_w: float
    mean_w: float
    phases: tuple[float, ...]
    coverage: float


def valid_samples(samples, max_gap_seconds=120):
    """Validate ordered samples. Refuse unreliable, negative or absurd readings."""
    out = []
    for s in sorted(samples, key=lambda x: x.timestamp):
        if not isfinite(s.watts) or not 0 <= s.watts <= 20000:
            continue
        if s.timestamp.tzinfo is None:
            continue
        if out and s.timestamp <= out[-1].timestamp:
            continue
        out.append(s)
    return out


def extract_cycles(samples, *, threshold_w=12.0, end_idle_minutes=5.0,
                   minimum_minutes=3.0, max_gap_seconds=120,
                   baseline_w=0.0):
    """Extract runs from a dedicated metered appliance.

    With a whole-house feed, this returns *unidentified load events*, never
    a verified washing-machine or dishwasher identity. Reject gaps, don't
    silently integrate across outages.
    """
    data = valid_samples(samples)
    if len(data) < 2:
        return []
    cycles = []
    start = None
    observed = []
    idle_since = None

    def finish():
        nonlocal start, observed, idle_since
        if start is None or len(observed) < 2:
            start, observed, idle_since = None, [], None
            return
        energy_wh = 0.0
        covered_seconds = 0.0
        peaks = []
        for a, b in zip(observed, observed[1:]):
            dt = (b.timestamp - a.timestamp).total_seconds()
            if not 0 < dt <= max_gap_seconds:
                start, observed, idle_since = None, [], None
                return
            pa = max(0.0, a.watts - baseline_w)
            pb = max(0.0, b.watts - baseline_w)
            energy_wh += (pa + pb) / 2 * dt / 3600
            covered_seconds += dt
            peaks.extend((pa, pb))
        duration = covered_seconds / 60
        if duration >= minimum_minutes:
            # 4-bin normalised temporal shape: lightweight fingerprint.
            slots = [[], [], [], []]
            for s in observed:
                fraction = (s.timestamp - observed[0].timestamp).total_seconds() / max(1, covered_seconds)
                slots[min(3, int(fraction * 4))].append(max(0, s.watts - baseline_w))
            phases = tuple(round(median(x), 1) if x else 0.0 for x in slots)
            cycles.append(Cycle(observed[0].timestamp, observed[-1].timestamp,
                                round(duration, 2), round(energy_wh / 1000, 4),
                                round(max(peaks), 1), round(energy_wh * 60 / duration, 1),
                                phases, 1.0))
        start, observed, idle_since = None, [], None

    for s in data:
        if observed:
            gap = (s.timestamp - observed[-1].timestamp).total_seconds()
            if gap > max_gap_seconds:
                finish()
        active = s.watts - baseline_w >= threshold_w
        if start is None:
            if active:
                start = s.timestamp
                observed = [s]
            continue
        observed.append(s)
        if active:
            idle_since = None
        elif idle_since is None:
            idle_since = s.timestamp
        elif (s.timestamp - idle_since).total_seconds() >= end_idle_minutes * 60:
            finish()
    finish()
    return cycles


def cycle_similarity(left, right):
    """0..1 heuristic similarity, not identity probability or proof."""
    if min(left.duration_minutes, right.duration_minutes, left.energy_kwh,
           right.energy_kwh) <= 0:
        return 0.0
    factors = [
        min(left.duration_minutes, right.duration_minutes) /
        max(left.duration_minutes, right.duration_minutes),
        min(left.energy_kwh, right.energy_kwh) /
        max(left.energy_kwh, right.energy_kwh),
        min(left.peak_w, right.peak_w) / max(left.peak_w, right.peak_w)
        if max(left.peak_w, right.peak_w) else 1.0,
    ]
    for a, b in zip(left.phases, right.phases):
        factors.append(1 - abs(a-b) / max(1.0, a, b))
    return round(max(0.0, sum(factors) / len(factors)), 3)


def rank_start_times(profile_kwh, slots, *, earliest, deadline,
                     max_import_kw=None, prefer_low_carbon=True):
    """Rank candidate start times for a measured energy profile.

    profile_kwh: per-slot appliance energy, e.g. [0.05,0.23,0.01].
    slots: contiguous equal-duration entries, each with start, carbon_g_kwh,
      grid_import_kwh_available (optional), forecast_valid. The optional
      available import capacity limits added load, not its carbon factor.
    Any missing/stale carbon data blocks a *carbon* recommendation.
    """
    if not profile_kwh or any(not isfinite(v) or v < 0 for v in profile_kwh):
        return []
    if sum(profile_kwh) <= 0:
        return []
    results = []
    count = len(profile_kwh)
    for i in range(0, len(slots) - count + 1):
        run = slots[i:i+count]
        if run[0]["start"] < earliest or run[-1]["end"] > deadline:
            continue
        if any(not item.get("forecast_valid", False) for item in run):
            continue
        if any(not isinstance(item.get("carbon_g_kwh"), (int, float)) or
               not isfinite(item["carbon_g_kwh"]) or item["carbon_g_kwh"] < 0
               for item in run):
            continue
        if any(run[j]["end"] != run[j+1]["start"] for j in range(len(run)-1)):
            continue
        if max_import_kw is not None and any(
            item.get("available_import_kw") is not None and
            (kwh / ((item["end"]-item["start"]).total_seconds()/3600)) >
            min(max_import_kw, item["available_import_kw"])
            for kwh, item in zip(profile_kwh, run)
        ):
            continue
        # Only count grid-supplied part. Local solar forecasts must be validated.
        grid_kwh = [
            min(kwh, max(0.0, float(item.get("projected_grid_kwh", kwh))))
            for kwh, item in zip(profile_kwh, run)
        ]
        emissions = sum(grid * item["carbon_g_kwh"] for grid, item in zip(grid_kwh, run))
        results.append({
            "start": run[0]["start"].isoformat(),
            "end": run[-1]["end"].isoformat(),
            "estimated_grid_kwh": round(sum(grid_kwh), 4),
            "estimated_gco2": round(emissions, 1),
            "evidence": "forecast_estimate",
            "action": "suggest_only",
        })
    return sorted(results, key=lambda x: (x["estimated_gco2"],
                                         x["estimated_grid_kwh"], x["start"]))
