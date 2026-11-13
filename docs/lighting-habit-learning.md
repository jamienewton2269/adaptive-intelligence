# Lighting Habit Learning v1 — v0.3.4

Developed by JNSystems. *In loving memory of Becki and Dad.*

## Objective

Learn when the household ordinarily turns a light on or off, without confusing
a person's intent with automation-controlled changes. Detect possible
energy-saving improvements in the longer term; never modify lighting in this
release.

## Scope and evidence

- Every genuine `light.*` state transition from `off` to `on` or vice versa,
  with a valid timezone-aware timestamp, enters the evidence counters.
- Brightness, colour and other same-state attribute updates are **not**
  counted as distinct switching events.
- Only actions attributed to a Home Assistant **user context** contribute
  toward manual on/off habits. Such attribution is not necessarily a physical
  Zigbee wall-button press.
- Known automation-context changes are counted separately, not treated as
  user choices. Unknown events are excluded from preference learning.
- Events with unavailable, invalid or stale lux are excluded from habit
  candidates. Missing/unconfigured lux remains a gap to close.
- Group by light, on/off, weekday/weekend, and local hour. Present evidence
  from distinct days, not merely how many times an automation repeated.
- Early signals require two distinct days. A repeat-pattern candidate needs
  at least five distinct days spanning ten or more days. Neither is authority
  to change a rule. No statistical probability is claimed.
- Records cover the last 45 days within the integration's bounded 5,000-event
  local history, whichever gives less coverage.
- Real occupancy and per-light energy cost are not yet measured by this
  module. They are mandatory future inputs before recommending a rule change.

## User interface

A new `Lighting Habits` tab is added to the existing `AI Diagnostics`
dashboard at `/ai-diagnostics/lighting-habits`. It displays counts, early
signals, repeat-pattern candidates, and their limitations.

New read-only sensors:
- `sensor.adaptive_intelligence_lighting_habit_candidates`
- `sensor.adaptive_intelligence_lighting_habit_early_patterns`

`adaptive_intelligence.lighting_habits` returns the report as read-only
service response data for other dashboard modules.

## Safety

This module adds no command path for lights, switches, heaters or appliances.
No cloud service, statistics broker or new persistent database.
No rules are changed. Any future adaptation requires evidence review,
presence/lux checks, expected energy impact and the user's approval.
