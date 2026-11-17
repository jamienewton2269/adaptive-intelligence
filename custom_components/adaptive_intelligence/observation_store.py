"""Bounded, meaningful local observation history (no actuator actions).

Do not allow high-frequency brightness/colour telemetry to evict genuine
on/off transitions and physical-input evidence. No old user intent is inferred.
"""
from datetime import datetime, timedelta, timezone


def is_useful_event(event):
    if not isinstance(event, dict):
        return False
    kind = event.get("kind")
    if kind == "physical_input":
        return bool(event.get("at") and event.get("signal"))
    if kind == "light":
        return (event.get("old") in ("on", "off")
                and event.get("new") in ("on", "off")
                and event["old"] != event["new"])
    if kind == "climate":
        return event.get("previous_target") != event.get("new_target")
    return False


def compact_observations(events, limit=5000, now=None, days=90):
    """Return recent meaningful events in original chronological order.

    Existing records are treated as evidence, not labels for a new model.
    Legacy attribute-only telemetry is pruned. Unparseable timestamps are
    excluded. Cap applies only after filtering to prevent data flooding.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware now required")
    cutoff = now - timedelta(days=days)
    retained = []
    for event in events:
        if not is_useful_event(event):
            continue
        try:
            at = datetime.fromisoformat(event["at"])
        except (TypeError, ValueError, KeyError):
            continue
        if at.tzinfo is None or not cutoff <= at <= now:
            continue
        retained.append(event)
    return retained[-limit:]
