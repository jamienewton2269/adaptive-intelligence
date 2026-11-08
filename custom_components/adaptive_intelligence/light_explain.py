"""Evidence-based, read-only explanations for lighting states.

Return confirmed blockers before hypotheses. Never infer command origin from
a lamp merely being on or off; automation traces are a separate evidence source.
"""
import re

# Explicitly verified HA-General lux priority model. Other lights can still be
# reported but require additional source mappings to establish their causes.
LUX_PRIORITY = {
    "light.snug_sofa_led": ("input_boolean.jns_lux_include_sofa", "input_number.jns_lux_rank_sofa"),
    "light.general_snug_corner": ("input_boolean.jns_lux_include_snug", "input_number.jns_lux_rank_snug"),
}
GLOBAL_PAUSE = "input_boolean.jns_lux_manual_hold_all"
MANUAL_OFF = "input_text.jns_lux_off_tonight_entities"
LUX = "sensor.jns_lighting_effective_lux"
LIGHT_AUTOMATION = "automation.general_shared_lux_progressive_control"


def match_light(query, lights):
    """Resolve exact entity ID, friendly name or short natural language query.

    Ambiguity is an explicit error, never a best-guess selection.
    """
    q = re.sub(r"[^a-z0-9]+", " ", str(query).lower()).strip()
    if not q:
        return {"status": "missing_query"}
    exact = [e for e in lights if q in (
        e.lower().replace("_", " ").replace(".", " "),
        str(lights[e].get("name", "")).lower(),
    )]
    if len(exact) == 1:
        return {"status": "found", "entity": exact[0]}
    terms = re.sub(
        r"\b(why|is|isnt|isn t|the|my|a|an|light|led|turning|turn|on|off|automatically|tonight|today|not|coming|up|doesnt|doesn t|are|was|did|come)\b",
        " ", q
    )
    terms = set(terms.split())
    matches = []
    for entity, data in lights.items():
        haystack = set(re.sub(r"[^a-z0-9]+", " ", entity+" "+str(data.get("name","")).lower()).split())
        if terms and terms <= haystack:
            matches.append(entity)
    if len(matches) == 1:
        return {"status": "found", "entity": matches[0]}
    return {"status": "ambiguous" if matches else "not_found", "candidates": matches[:10]}


def explain_light(entity, states):
    """states maps entity IDs to dictionaries with 'state' and optional 'name'."""
    source = states.get(entity)
    if not source:
        return {"status": "not_found", "answer": "This light is not registered in Home Assistant."}
    current = source.get("state", "unknown")
    causes = []
    context = []
    if current in ("unknown", "unavailable"):
        causes.append({"certainty": "confirmed", "code": "device_unavailable",
                       "detail": "Home Assistant cannot confirm the device's current power state."})
    configured = LUX_PRIORITY.get(entity)
    if configured:
        include, rank = configured
        if states.get(include, {}).get("state") == "off":
            causes.append({"certainty": "confirmed", "code": "excluded_from_lux",
                           "detail": "This light is excluded from the automatic lux priority ladder.",
                           "evidence": include})
        context.append({"name": "lux_priority_position",
                        "value": states.get(rank, {}).get("state", "unknown")})
    if states.get(GLOBAL_PAUSE, {}).get("state") == "on":
        causes.append({"certainty": "confirmed", "code": "global_automatic_pause",
                       "detail": "The global evening lux automation pause is enabled.",
                       "evidence": GLOBAL_PAUSE})
    manual_off_text = str(states.get(MANUAL_OFF, {}).get("state", ""))
    if entity in re.split(r"[,;\s]+", manual_off_text):
        causes.append({"certainty": "confirmed", "code": "manual_off_tonight",
                       "detail": "This light is listed as manually switched off for tonight.",
                       "evidence": MANUAL_OFF})
    automation = states.get(LIGHT_AUTOMATION, {}).get("state", "unknown")
    if automation == "off":
        causes.append({"certainty": "confirmed", "code": "automation_disabled",
                       "detail": "The shared lux progressive-control automation is disabled.",
                       "evidence": LIGHT_AUTOMATION})
    context.extend([
        {"name": "light_state", "value": current},
        {"name": "effective_lux", "value": states.get(LUX, {}).get("state", "unknown")},
        {"name": "lux_automation", "value": automation},
    ])
    name = source.get("name") or entity
    if causes:
        details = " ".join(c["detail"] for c in causes)
        answer = (f"{name} currently reports {current}. {details} "
                  "This explains the configured automatic-control blockers; "
                  "it does not prove who last operated the light.")
        certainty = "confirmed_configuration"
    else:
        answer = (f"{name} currently reports {current}. No known configured blocker "
                  "was found in the inspected rules. The exact cause cannot yet be "
                  "established without the relevant automation traces and device events.")
        certainty = "incomplete_evidence"
    return {"status": "ok", "entity": entity, "answer": answer,
            "certainty": certainty, "causes": causes, "context": context,
            "read_only": True}
