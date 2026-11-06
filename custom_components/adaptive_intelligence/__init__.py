"""Passive Adaptive Intelligence by JNSystems: observe, don't actuate."""
from __future__ import annotations
from collections import deque
from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_CALL_SERVICE
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from .const import DOMAIN, STORAGE_VERSION, STORAGE_KEY, MAX_EVENTS
from .engine import classify, make_suggestions

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    saved = await store.async_load() or {}
    events = deque(saved.get("events", [])[-MAX_EVENTS:], maxlen=MAX_EVENTS)
    state = {"events": events, "suggestions": [], "last_save": None}
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state
    automation_contexts = {}
    service_contexts = {}
    recent_light_actions = {}

    @callback
    def forget_stale(now):
        cutoff = now - timedelta(minutes=5)
        for d in (automation_contexts, service_contexts, recent_light_actions):
            for key, value in tuple(d.items()):
                when = value[0] if isinstance(value, tuple) else value
                if when < cutoff:
                    del d[key]

    @callback
    def handle_automation(event):
        if event.context.id:
            automation_contexts[event.context.id] = dt_util.utcnow()

    @callback
    def handle_service(event):
        if event.data.get("domain") not in ("light", "homeassistant", "scene", "script"):
            return
        if event.context.id:
            service_contexts[event.context.id] = dt_util.utcnow()

    @callback
    def handle_state(event):
        entity = event.data.get("entity_id", "")
        if not entity.startswith(("light.", "climate.")):
            return
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if not new or not old or old.state in ("unavailable", "unknown"):
            return
        if old.state == new.state and old.attributes == new.attributes:
            return
        if new.state in ("unavailable", "unknown"):
            return
        context = {"id": new.context.id, "parent_id": new.context.parent_id, "user_id": new.context.user_id}
        classification = classify(context, automation_contexts, service_contexts)
        action = {
            "at": new.last_updated.isoformat(), "entity": entity,
            "kind": "light" if entity.startswith("light.") else "climate",
            "old": old.state, "new": new.state,
            "classification": classification, "override": False, "context": context,
        }
        lux_id = entry.data.get("lux_entity", "")
        if lux_id:
            lux = hass.states.get(lux_id)
            try:
                action["lux"] = float(lux.state) if lux else None
            except (TypeError, ValueError):
                action["lux"] = None
        if entity.startswith("light.") and old.state != new.state:
            last = recent_light_actions.get(entity)
            if classification == "user" and last and last[1] == "automation" and last[2] != new.state:
                action["override"] = True
            recent_light_actions[entity] = (dt_util.utcnow(), classification, new.state)
        events.append(action)

    async def persist(_=None):
        forget_stale(dt_util.utcnow())
        try:
            state["suggestions"] = make_suggestions(list(events), hass.config.time_zone)
            await store.async_save({"events": list(events)})
            state["last_save"] = dt_util.utcnow().isoformat()
        except Exception:
            _LOGGER.exception("Unable to persist adaptive learning observations")

    unsubscribers = [
        hass.bus.async_listen("automation_triggered", handle_automation),
        hass.bus.async_listen(EVENT_CALL_SERVICE, handle_service),
        hass.bus.async_listen(EVENT_STATE_CHANGED, handle_state),
        async_track_time_interval(hass, persist, timedelta(minutes=5)),
    ]
    entry.async_on_unload(lambda: [unsub() for unsub in unsubscribers])
    entry.async_on_unload(lambda: hass.async_create_task(persist()))
    state["suggestions"] = make_suggestions(list(events), hass.config.time_zone)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if ok:
        entry.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
