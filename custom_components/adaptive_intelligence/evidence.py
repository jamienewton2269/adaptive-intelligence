"""Pure, conservative physical-input evidence helpers.

JNSystems — in loving memory of Becki and Dad.
Device event evidence is NOT proof of a lighting override.
"""
from datetime import datetime, timedelta


def physical_input(entity_id, old_state, new_state, at):
    """Recognise HA event entities and Zigbee2MQTT action sensors.

    No MQTT subscription and no actuator access. No inferred target light.
    Returns metadata suitable for local historical storage, or None.
    """
    if not entity_id or not new_state:
        return None
    action = str(new_state).strip()
    if action.lower() in ("unknown", "unavailable", "none", ""):
        return None
    if old_state == new_state:
        return None
    if entity_id.startswith("event."):
        category = "event_entity"
    elif entity_id.startswith("sensor.") and entity_id.endswith("_action"):
        category = "action_sensor"
    else:
        return None
    # Limit stored material to bounded strings. No event payload, IDs or credentials.
    return {
        "at": at.isoformat(),
        "entity": entity_id[:255],
        "kind": "physical_input",
        "signal": action[:80],
        "signal_type": category,
        "classification": "physical_candidate",
        "override": False,
    }


def recent_candidate(events, changed_at, window=timedelta(seconds=15)):
    """Check proximity only. Without device mapping, never assert a match."""
    return any(
        event.get("kind") == "physical_input"
        and event.get("at")
        and abs(changed_at - datetime.fromisoformat(event["at"])) <= window
        for event in events
        if event.get("at")
    )


def classify_quality(event):
    """Compact diagnostic classification for dashboards."""
    if event.get("kind") == "physical_input":
        return "physical_input_unverified"
    if event.get("kind") == "light" and event.get("lux_quality") not in (None, "valid", "unconfigured"):
        return "lux_unreliable"
    return event.get("classification", "unknown")
