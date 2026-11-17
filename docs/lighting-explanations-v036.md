# v0.3.6 lighting explanation development (not deployed)

This branch adds a pure, read-only event explanation formatter and regression
tests. It does **not** install a dashboard, register a new service, change the
running v0.3.5 integration, or enable learned actions.

## Evidence boundary

An HA state context classified as automation is **not** proof of the exact
automation or its rationale. A user context is not automatically a physical
Zigbee press. Unmapped Zigbee actions remain independent observations.
A missing manual override flag does not prove a manual choice was respected.
Outdoor lux at an observation is context, not proof it triggered a threshold.

## Next integration steps

1. Verify live v0.3.5 installation, history and sensor entity IDs through Node C.
2. Add bounded brightness-transition capture without admitting colour telemetry.
3. Capture immutable decision-time evidence and correlate automation trace IDs
   only when demonstrably linked.
4. Expose a read-only recent-light-decisions response and a household dashboard
   section titled 'Why did my lights change?'.
5. Run all regression tests, HA config validation and dashboard acceptance checks
   before a controlled deployment. Preserve existing automations and history.

No observations become automation rules without explicit approval.
