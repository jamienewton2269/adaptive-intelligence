"""Read-only sensors: evidence counts, no actuator services."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_METRICS = (
    "observations", "suggestions", "verified_user_actions",
    "unclassified_actions", "heating_changes",
    "physical_input_candidates", "unreliable_lux_events",
)


async def async_setup_entry(hass, entry, async_add_entities):
    sensors = [AdaptiveSensor(hass, entry, metric) for metric in _METRICS]
    hass.data[DOMAIN][entry.entry_id]["sensors"].extend(sensors)
    async_add_entities(sensors)


class AdaptiveSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, entry, metric):
        self.hass = hass
        self.entry = entry
        self.metric = metric
        self._attr_unique_id = f"{entry.entry_id}_{metric}"
        self._attr_name = "Adaptive Intelligence " + metric.replace("_", " ").title()

    @property
    def native_value(self):
        data = self.hass.data[DOMAIN][self.entry.entry_id]
        events = data["events"]
        if self.metric == "observations":
            return len(events)
        if self.metric == "suggestions":
            return len(data["suggestions"])
        if self.metric == "verified_user_actions":
            return sum(e.get("classification") == "user" for e in events)
        if self.metric == "unclassified_actions":
            return sum(e.get("classification") == "unknown" for e in events)
        if self.metric == "heating_changes":
            return sum(e.get("kind") == "climate" for e in events)
        if self.metric == "physical_input_candidates":
            return sum(e.get("kind") == "physical_input" for e in events)
        if self.metric == "unreliable_lux_events":
            return sum(e.get("lux_quality") in ("invalid", "stale", "unavailable") for e in events)
        return 0

    @property
    def extra_state_attributes(self):
        data = self.hass.data[DOMAIN][self.entry.entry_id]
        if self.metric == "suggestions":
            return {"candidates": data["suggestions"][:10], "mode": "observe_only"}
        if self.metric == "observations":
            return {
                "last_save": data["last_save"], "last_event": data["last_event"],
                "mode": "observe_only", "history_limit": 5000,
            }
        return {"mode": "observe_only"}
