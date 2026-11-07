# Adaptive Intelligence

A local-first, observation-only learning integration for Home Assistant.

**Developed by JNSystems**

*In loving memory of Becki and Dad.*

## Release 0.2.0 — evidence quality

The engine observes light and climate state changes without controlling devices.
- Captures verified Home Assistant user actions, automation contexts, and unknown origin events separately.
- Records thermostat setpoint and HVAC mode changes rather than counting ambient temperature fluctuations as user requests.
- Records optional external illuminance and flags unavailable, implausible or stale readings.
- Requires repeated, corroborated observations before presenting a diagnostic candidate.
- Adds five diagnostic sensors, including evidence classification and heating changes.

**Physical Zigbee button attribution is not yet established.** Events lacking a trustworthy Home Assistant context remain unknown. Heating suggestions, approval pop-ups and autonomous control are not implemented.

## Installation and updates

Add `https://github.com/jamienewton2269/adaptive-intelligence` to HACS/Marketplace as a custom **Integration** repository, install and restart Home Assistant. Add **Adaptive Intelligence** under Settings → Devices & services.

For upgrades, preserve the existing configuration entry and local `.storage/adaptive_intelligence.history` file. Do not clear the history during updates.

## Dashboard

[Read-only Lovelace dashboard YAML](docs/learning-dashboard.yaml) can be added to a new dashboard manually. Its existence in the repository does not automatically install it into Home Assistant.

## Safety and privacy

All event records remain local to Home Assistant. No telemetry, external ML API, control service, light commands or heating commands. Incorrect unknown/manual identification must never raise rule confidence.

## Documentation and original artwork

See [documentation and dedication](docs/README.md). The original Becki cartoon and animated JNSystems GIF must be preserved without alterations. Public-facing integration remains named Adaptive Intelligence.

## Tests

`python3 -m unittest discover -s tests -v`

## Licence

This repository currently uses the [GPL-3.0 licence](LICENSE).
