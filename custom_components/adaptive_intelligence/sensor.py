"""Read-only sensors expose learning state and candidate suggestions."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AdaptiveSensor(hass, entry, "observations"), AdaptiveSensor(hass, entry, "suggestions")])

class AdaptiveSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, entry, metric):
        self.hass = hass
        self.entry = entry
        self.metric = metric
        self._attr_unique_id = f"{entry.entry_id}_{metric}"
        self._attr_name = "Adaptive Intelligence " + metric.title()

    @property
    def native_value(self):
        data = self.hass.data[DOMAIN][self.entry.entry_id]
        return len(data["events"] if self.metric == "observations" else data["suggestions"])

    @property
    def extra_state_attributes(self):
        data = self.hass.data[DOMAIN][self.entry.entry_id]
        if self.metric == "suggestions":
            return {"candidates": data["suggestions"][:10], "mode": "observe_only"}
        return {"last_save": data["last_save"], "mode": "observe_only"}
