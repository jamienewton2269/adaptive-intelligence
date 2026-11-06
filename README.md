# Adaptive Intelligence

An experimental, local-first, **observation-only** learning integration for Home Assistant.

**Developed by JNSystems**

*In loving memory of Becki and Dad.*

Adaptive Intelligence observes changes to light and climate entities, records context and optional outdoor lux measurements, and builds conservative candidate patterns for review. The first release **does not operate lights, heating or existing automations**.

## Install with HACS / Marketplace

1. Add `https://github.com/jamienewton2269/adaptive-intelligence` as a custom **Integration** repository.
2. Download Adaptive Intelligence and restart Home Assistant.
3. Open Settings → Devices & services → Add integration → Adaptive Intelligence.
4. Optionally provide an outdoor lux sensor entity ID.
5. Review the new diagnostic sensors and log entries. This is a development release, not yet production validated.

## Current limitations

Physical Zigbee switch events without a trustworthy Home Assistant context are deliberately classified as unknown rather than assumed manual overrides. Suggestions are diagnostic candidates, not approved automation changes. Heating intelligence and interactive suggestion approvals are planned, not delivered.

## Documentation and artwork

See [documentation and dedication](docs/README.md). The original Becki cartoon and animated JNSystems GIF are reserved for the documentation artwork and must not be replaced by lookalikes. The complete original artwork is included in the v0.1.3 downloadable project archive while GitHub artwork publication is completed.

## Privacy and safety

No cloud processing, external telemetry, or light/heating service commands. Event history remains on the Home Assistant instance under its local storage system.

## Licence

See [LICENSE](LICENSE).
