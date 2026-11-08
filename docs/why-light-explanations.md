# Explain a light — evidence-based diagnostics

This feature accepts a natural-language text query and returns a **read-only**
explanation from current Home Assistant state. It cannot switch a light on or
off or alter existing automations.

## First verified example

`Why isn't the Snug Sofa LED turning on automatically tonight?`

HA-General currently reports that `input_boolean.jns_lux_include_sofa` is
**off**. The sofa LED is therefore excluded from the priority-lux lighting
ladder. The LED's actual state can still be **on** from some other source;
its present state does not prove who operated it.

The entity-specific associations are deliberately explicit. For lights not
yet mapped to a documented controller, the system will explain that the
evidence is incomplete rather than hallucinating a cause.

## Query interface

In Home Assistant, Settings → Developer Tools → Actions:

- Action: `adaptive_intelligence.explain_light`
- Question: `Why isn't the Snug Sofa LED turning on automatically tonight?`
- The action returns `answer`, `causes`, `context`, `certainty`, and
  `read_only`. The action must be invoked with response data.

This is a **plain-text query service**, not yet a Home Assistant Assist
conversation-agent integration. Future work should connect it to Assist
and gather actual automation traces, Zigbee events and device health in
the diagnostic evidence store.

## Safety and limitations

- No controls, no actuator service calls, no additional cloud dependencies.
- A disabled inclusion helper is **confirmed configuration evidence**; it
  is not proof that a particular trigger occurred or failed at a given time.
- When reasons cannot be determined, return `incomplete_evidence`.
- UI wording avoids claims of action provenance without an automation trace.
- Relevant controller rules must be explicitly mapped and tested as they
  are discovered.

Developed by JNSystems. In memory of Becki and Dad.
