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


# Generic words carry no identifying value. Stopwords are only discarded
# for matching; the original question is retained verbatim for diagnostics.
_QUERY_STOP = {
    "why", "is", "isnt", "isn", "t", "the", "my", "a", "an", "light",
    "lights", "led", "lamp", "bulb", "turning", "turn", "turned",
    "on", "off", "automatically", "automatic", "tonight", "today",
    "not", "coming", "come", "doesnt", "doesn", "are", "was", "did",
    "will", "has", "have", "please", "in", "at", "to", "from", "of",
    "work", "working", "switch", "switched", "staying", "stay",
    "up", "down", "now", "this", "that", "why's",
}
# Explicitly named composites and conventional terms; safe because they are
# lexical normalisation only, not a claim about a device's control wiring.
_COMPOSITES = (
    ("livingroom", "living room"),
    ("frontdoor", "front door"),
    ("bedroompendant", "bedroom pendant"),
    ("worktop", "work top"),
    ("treehouse", "tree house"),
    ("snugsofa", "snug sofa"),
    ("hallway", "hall way"),
)
_VARIANTS = {
    "sofa": "sofa", "settee": "sofa", "couch": "sofa",
    "lounge": "living", "living": "living",
    "pendant": "pendant", "ceiling": "pendant",
    "strip": "strip", "tape": "strip",
    "wc": "wc", "toilet": "wc", "loo": "wc",
    "hallway": "hall", "hall": "hall",
    "bulbs": "bulb", "lamps": "lamp",
}
_FIXTURE_WORDS = {"pendant", "strip", "sofa", "corner", "front",
                  "door", "work", "top", "tripod", "ceiling", "bedroom"}


def _tokens(text):
    value = str(text or "").lower()
    value = value.replace("_", " ").replace(".", " ")
    for compact, spaced in _COMPOSITES:
        value = value.replace(compact, spaced)
    value = re.sub(r"([a-z])([0-9])", r"\\1 \\2", value)
    raw = re.findall(r"[a-z]+|[0-9]+", value)
    return tuple(_VARIANTS.get(t, t) for t in raw)


def _light_tokens(entity, data):
    entity_words = _tokens(entity.removeprefix("light."))
    name_words = _tokens(data.get("name", ""))
    aliases = data.get("aliases") or ()
    if isinstance(aliases, str):
        aliases = (aliases,)
    return set(entity_words + name_words + tuple(
        token for alias in aliases for token in _tokens(alias)
    ))


def match_light(query, lights):
    """Find a light from a natural phrase, without guessing between candidates.

    Handles compact entity IDs (livingroom), ordinary spacing, friendly names,
    fixture synonyms and optional HA registry aliases. Room-only requests
    return ambiguity if more than one light is a plausible match.
    """
    words = _tokens(query)
    if not words:
        return {"status": "missing_query", "candidates": []}
    terms = set(words) - _QUERY_STOP
    if not terms:
        return {"status": "missing_query", "candidates": []}

    exact = [
        entity for entity, data in lights.items()
        if tuple(words) == _tokens(entity) or
        tuple(words) == _tokens(data.get("name", "")) or
        tuple(words) in [tuple(_tokens(alias)) for alias in (
            data.get("aliases") if isinstance(data.get("aliases"), (list, tuple))
            else [data.get("aliases", "")]
        )]
    ]
    if len(exact) == 1:
        return {"status": "found", "entity": exact[0]}

    # Require every meaningful query word to appear in a candidate's
    # entity/name/alias. No arbitrary edit distance that could select the
    # wrong physical actuator.
    matched = [
        e for e, data in lights.items()
        if terms <= _light_tokens(e, data)
    ]
    if len(matched) == 1:
        return {"status": "found", "entity": matched[0]}
    if len(matched) > 1:
        return {"status": "ambiguous", "candidates": sorted(matched)[:15]}

    # Device may be named 'livingroom pendant' while user asks 'living room
    # light'. For partial names, accept an unambiguous *location* only.
    # Do not drop discriminators such as sofa, corner or front door.
    candidates = []
    for e, data in lights.items():
        tok = _light_tokens(e, data)
        remaining = terms - tok
        if not remaining:
            candidates.append(e)
        elif remaining <= {"room"} and "living" in tok and "living" in terms:
            candidates.append(e)
    if len(candidates) == 1:
        return {"status": "found", "entity": candidates[0]}
    if candidates:
        return {"status": "ambiguous", "candidates": sorted(candidates)[:15]}
    return {"status": "not_found", "candidates": []}


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
