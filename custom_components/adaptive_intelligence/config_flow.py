"""UI configuration: install once with no external accounts."""
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol
from .const import DOMAIN

class AdaptiveIntelligenceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Adaptive Intelligence", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Optional("lux_entity", default=""): str}),
        )
