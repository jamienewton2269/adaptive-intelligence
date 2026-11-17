"""Conservative Zigbee2MQTT action topic parser.

This establishes *physical-input candidates*, never which light was
controlled. Only JSON-free Zigbee action topics are accepted; no cloud,
credentials, MQTT connection or Home Assistant API is used here.
"""
import re


def parse_zigbee_action(topic, payload, at):
    if not isinstance(topic, str) or not topic.startswith("zigbee2mqtt/"):
        return None
    parts=topic.split("/")
    if len(parts)!=3 or parts[2]!="action":
        return None
    device=parts[1].strip()
    if not device or len(device)>120 or device in ("bridge", "+", "#"):
        return None
    if isinstance(payload, bytes):
        try:
            payload=payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(payload,str):
        return None
    action=payload.strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_\\-]{0,79}",action):
        return None
    return {
        "at":at.isoformat(),
        "entity":topic[:255],
        "kind":"physical_input",
        "signal":action,
        "signal_type":"zigbee2mqtt_action_topic",
        "classification":"physical_candidate",
        "override":False,
        "verified_target":False,
    }
