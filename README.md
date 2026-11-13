# Adaptive Intelligence

A lightweight, local-first, **observation-only** learning integration for Home Assistant.

**Developed by JNSystems**

*In loving memory of Becki and Dad.*

## v0.3.0: learning evidence and physical-input candidates

Adaptive Intelligence records light and heating state changes with cautious source classification. New in v0.3:

- **Physical-input candidates:** Home Assistant `event.*` entities and `sensor.*_action` changes are recorded separately, without treating them as verified manual lighting overrides. This can include Zigbee2MQTT action entities when exposed by Home Assistant.
- **Evidence-quality sensors:** Physical candidate count and unreliable-lux count join the five existing diagnostic sensors (seven total).
- **Heating evidence:** Records changes in requested heating setpoints/modes, not ambient temperature fluctuations.
- **Conservative learning:** Unknown source actions and invalid/stale lux never build confidence toward automatic changes.
- **No new dependencies or external processing.** Local history is capped at 5,000 events.

### Important limitations

There is not yet a verified mapping from physical button presses to particular lights. Physical events are therefore only candidates. No learning model should assume these changed a specific lamp. The optional lux sensor remains unconfigured on the current HA-General installation. Approval pop-ups, heating recommendations, and automatic control are **not** implemented. Observations are diagnostic data, not authoritative evidence of intent.

## Install or upgrade

Add `https://github.com/jamienewton2269/adaptive-intelligence` as a HACS/Marketplace custom **Integration** repository; download, restart Home Assistant and add **Adaptive Intelligence** in Devices & services. Existing instances should upgrade in place without removing the configuration entry or deleting `.storage/adaptive_intelligence.history`.

## Dashboard

The [read-only Lovelace YAML example](docs/learning-dashboard.yaml) can be imported as a separate dashboard. It is not automatically installed when updating the integration.

## Testing

`python3 -m unittest discover -s tests -v` — 11 tests in v0.3.

## Safety and privacy

No actuator commands, no changes to existing automations, no telemetry and no third-party AI service. Read-only observation only.

## Artwork and dedication

See [documentation](docs/README.md). The original Becki cartoon and animated JNSystems logo should be displayed side by side when published. Do not use substitutes.

## Licence

This repository currently uses [GPL-3.0](LICENSE).


## Appliance energy intelligence — research prototype

[Appliance fingerprinting and carbon-aware scheduling design](docs/appliance-energy-intelligence.md) describes an observation-only extension to learn power-cycle shapes and rank user-approved washing-machine and dishwasher run windows against NESO regional grid-carbon forecasts and estimated grid import. Its pure analysis functions and tests are committed, but **live appliance learning is not yet enabled**. The Zigbee meter's power/current/energy readings are presently unknown; identification of shared-household loads must remain unverified until readings and labels are confirmed.


## Explain a light (v0.3.1)

The new read-only `adaptive_intelligence.explain_light` service accepts a plain-English `query` and returns confirmed configuration blockers, current state and the evidence used. [See explanation documentation](docs/why-light-explanations.md). It identifies the Snug Sofa LED as excluded from the automatic lux priority ladder when `input_boolean.jns_lux_include_sofa` is off. Other lights without a verified rule mapping return incomplete evidence instead of a fabricated answer. Unit tests pass; Home Assistant Assist voice/chat integration and automation-trace collection remain future work. No lighting commands or automation changes.


## Dedicated AI Diagnostics dashboard

The optional [YAML dashboard](dashboard/ai-diagnostics.yaml) and [native custom question card](dashboard/adaptive-explain-card.js) provide a separate **AI Diagnostics** sidebar entry with five views: Ask why, Lighting, Heating, Energy and System. On HA-General the URL is `/ai-diagnostics/ask`. The question card uses Home Assistant's authenticated WebSocket connection to request `adaptive_intelligence.explain_light` with `return_response: true`; it never issues lighting commands. The dashboard is installed on HA-General but other installations must register the resource `/local/adaptive-intelligence/adaptive-explain-card.js` and the YAML dashboard in their own `configuration.yaml`. The card's end-to-end response needs live frontend acceptance testing.


## v0.3.4 — Lighting Habit Learning v1

The read-only [Lighting Habits dashboard](dashboard/ai-diagnostics.yaml) shows
repeatable on/off times independently of automations and brightness updates.
The engine distinguishes `early_patterns` (at least two separate days) from
`candidates` (at least five distinct days spanning ten or more days);
separately for each light, weekday/weekend and on/off action. Only verified
Home Assistant user-context transitions may contribute to a manual pattern.
Unattributed physical Zigbee events remain unverified, not assumed manual.
Two new diagnostics sensors and the `adaptive_intelligence.lighting_habits`
read-only service expose the evidence. All existing automations remain untouched.

[Read the habit-learning evidence and limitations](docs/lighting-habit-learning.md).
