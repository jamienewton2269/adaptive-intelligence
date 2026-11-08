"""Adaptive Intelligence: no commands, no cloud, no inference from uncertain origin.

Developed by JNSystems. In memory of Becki and Dad.
"""
from __future__ import annotations

from collections import deque
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, callback, SupportsResponse
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_CALL_SERVICE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORAGE_VERSION, STORAGE_KEY, MAX_EVENTS
from .engine import classify, make_suggestions, validated_lux
from .evidence import physical_input, classify_quality
from .light_explain import match_light, explain_light

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    saved = await store.async_load() or {}
    events = deque(saved.get("events", [])[-MAX_EVENTS:], maxlen=MAX_EVENTS)
    state = {"events": events, "suggestions": [], "last_save": None,
             "last_event": None, "sensors": []}
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state

    automation_contexts = {}
    service_contexts = {}
    recent_light_actions = {}
    sensors = state["sensors"]

    @callback
    def forget_stale(now):
        cutoff = now - timedelta(minutes=5)
        for dictionary in (automation_contexts, service_contexts, recent_light_actions):
            for key, value in tuple(dictionary.items()):
                when = value[0] if isinstance(value, tuple) else value
                if when < cutoff:
                    del dictionary[key]

    @callback
    def update_sensors():
        for sensor in sensors:
            if sensor.hass is not None:
                sensor.async_write_ha_state()

    @callback
    def handle_automation(event):
        if event.context.id:
            automation_contexts[event.context.id] = dt_util.utcnow()

    @callback
    def handle_service(event):
        if event.data.get("domain") not in ("light", "homeassistant", "scene", "script", "climate"):
            return
        if event.context.id:
            service_contexts[event.context.id] = dt_util.utcnow()

    @callback
    def handle_state(event):
        entity = event.data.get("entity_id", "")
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if not new or not old:
            return
        now = dt_util.utcnow()
        if entity.startswith("event.") or (
            entity.startswith("sensor.") and entity.endswith("_action")
        ):
            # Physical input is only a candidate, never inferred to control a lamp.
            candidate = physical_input(entity, old.state, new.state, now)
            if candidate is not None:
                events.append(candidate)
                state["last_event"] = candidate["at"]
                update_sensors()
            return

        if not entity.startswith(("light.", "climate.")):
            return
        if old.state in ("unavailable", "unknown") or new.state in ("unavailable", "unknown"):
            return
        if old.state == new.state and old.attributes == new.attributes:
            return

        kind = "light" if entity.startswith("light.") else "climate"
        context = {"id": new.context.id, "parent_id": new.context.parent_id,
                   "user_id": new.context.user_id}
        classification = classify(context, automation_contexts, service_contexts)
        action = {
            "at": now.isoformat(), "entity": entity, "kind": kind,
            "old": old.state, "new": new.state,
            "classification": classification, "override": False,
        }
        if kind == "climate":
            keys = ("temperature", "target_temp_high", "target_temp_low", "hvac_mode")
            before = {k: old.attributes.get(k) for k in keys}
            after = {k: new.attributes.get(k) for k in keys}
            if before == after and old.state == new.state:
                return
            action["previous_target"] = before
            action["new_target"] = after
        else:
            lux_id = entry.options.get("lux_entity", entry.data.get("lux_entity", ""))
            if lux_id:
                lux, quality = validated_lux(hass.states.get(lux_id), now)
                action["lux"], action["lux_quality"] = lux, quality
            if old.state != new.state:
                last = recent_light_actions.get(entity)
                if (classification == "user" and last
                        and last[1] == "automation" and last[2] != new.state
                        and (now - last[0]) <= timedelta(minutes=5)):
                    action["override"] = True
                recent_light_actions[entity] = (now, classification, new.state)

        events.append(action)
        state["last_event"] = now.isoformat()
        update_sensors()

    async def persist(_=None):
        forget_stale(dt_util.utcnow())
        try:
            state["suggestions"] = make_suggestions(list(events), hass.config.time_zone)
            await store.async_save({"events": list(events)})
            state["last_save"] = dt_util.utcnow().isoformat()
            update_sensors()
        except Exception:
            _LOGGER.exception("Unable to persist adaptive learning observations")

    entry.async_on_unload(
        hass.bus.async_listen("automation_triggered", handle_automation)
    )
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_CALL_SERVICE, handle_service)
    )
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_STATE_CHANGED, handle_state)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, persist, timedelta(minutes=5))
    )
    entry.async_on_unload(lambda: hass.async_create_task(persist()))
    state["suggestions"] = make_suggestions(list(events), hass.config.time_zone)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    @callback
    def explain_light_query(call):
        # Read-only service. Resolve ambiguity explicitly rather than guessing.
        query = call.data["query"]
        lights = {
            obj.entity_id: {"name": obj.attributes.get("friendly_name", ""),
                            "state": obj.state}
            for obj in hass.states.async_all()
            if obj.entity_id.startswith("light.")
        }
        match = match_light(query, lights)
        if match["status"] != "found":
            return {"status": match["status"],
                    "answer": "Could not identify one light from that question.",
                    "candidates": match.get("candidates", []),
                    "read_only": True}
        facts = {
            obj.entity_id: {"name": obj.attributes.get("friendly_name", ""),
                            "state": obj.state}
            for obj in hass.states.async_all()
            if obj.entity_id.startswith(("light.", "input_boolean.",
                                         "input_number.", "input_text.",
                                         "sensor.", "automation."))
        }
        return explain_light(match["entity"], facts)

    hass.services.async_register(
        DOMAIN, "explain_light", explain_light_query,
        schema=vol.Schema({vol.Required("query"): vol.All(str, vol.Length(min=1, max=512))}),
        supports_response=SupportsResponse.ONLY,
    )
    entry.async_on_unload(lambda: hass.services.async_remove(DOMAIN, "explain_light"))
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if ok:
        entry.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
