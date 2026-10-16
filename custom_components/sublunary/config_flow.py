"""Config and options flow. Only the refresh tick is configurable; VoC
definitions are entities that users enable or disable."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .const import CONF_TICK_MINUTES, DEFAULT_TICK_MINUTES, DOMAIN


def _schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TICK_MINUTES, default=DEFAULT_TICK_MINUTES): NumberSelector(
            NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
    })


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    return {**user_input, CONF_TICK_MINUTES: int(user_input[CONF_TICK_MINUTES])}


class SublunaryConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Sublunary", data={}, options=_clean(user_input))
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return SublunaryOptionsFlow()


class SublunaryOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_clean(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_schema(), self.config_entry.options),
        )
