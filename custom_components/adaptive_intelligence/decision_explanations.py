"""Conservative, read-only human explanations for observed lighting changes.

No Home Assistant imports: safe to unit test without an HA installation.
"""
from __future__ import annotations


def describe_transition(event):
    """Describe an observation without inventing automation provenance."""
    if event.get("kind") != "light":
        return None
    old, new = event.get("old"), event.get("new")
    if old == new:
        if event.get("old_brightness") == event.get("new_brightness"):
            return None
        change = "Changed brightness"
    elif new == "on":
        change = "Turned ON"
    elif new == "off":
        change = "Turned OFF"
    else:
        return None

    origin = event.get("classification", "unknown")
    # Context classification is evidence, not a verified execution trace.
    sources = {
        "automation": "Possibly an automation (trace not verified)",
        "user": "Home Assistant user action",
        "unknown": "Cause not yet confirmed",
    }
    source = sources.get(origin, "Cause not yet confirmed")
    lux = event.get("lux")
    quality = event.get("lux_quality")
    lux_text = (
        f"{lux} lux from the external sensor"
        if lux is not None and quality == "valid"
        else "Outdoor brightness was not reliably available"
    )
    override = (
        "A recent automation decision was reversed by a user"
        if event.get("override") is True
        else "Whether an earlier manual choice was respected is not verified"
    )
    return {
        "entity": event.get("entity"),
        "at": event.get("at"),
        "change": change,
        "source": source,
        "reason": "No verified triggering rule or automation trace is recorded",
        "outdoor_brightness": lux_text,
        "learning_status": "Observation only; not an approved learned rule",
        "manual_preference": override,
        "certainty": "partial" if origin in ("user", "automation") else "unknown",
        "read_only": True,
    }


def recent_explanations(events, limit=10):
    """Return most recent lighting decisions, preserving source history."""
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    result = []
    for event in reversed(events):
        explanation = describe_transition(event)
        if explanation is not None:
            result.append(explanation)
            if len(result) >= limit:
                break
    return result
