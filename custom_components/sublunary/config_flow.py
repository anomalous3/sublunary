"""Config and options flow: the refresh tick, and an optional natal chart
(birth moment, timezone, place, house system) for the Moon's natal house.
VoC definitions are entities that users enable or disable."""

from __future__ import annotations

import zoneinfo
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DateTimeSelector, LocationSelector, LocationSelectorConfig,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
)

from .const import (
    CONF_BIRTH, CONF_BIRTH_LOCATION, CONF_BIRTH_TZ, CONF_HOUSE_SYSTEM, CONF_TICK_MINUTES,
    DEFAULT_TICK_MINUTES, DOMAIN, HOUSE_SYSTEMS,
)


def _schema(default_tz: str) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TICK_MINUTES, default=DEFAULT_TICK_MINUTES): NumberSelector(
            NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
        # natal chart, optional: enables the Moon's natal house
        vol.Optional(CONF_BIRTH): DateTimeSelector(),
        vol.Optional(CONF_BIRTH_TZ, default=default_tz): SelectSelector(SelectSelectorConfig(
            options=sorted(zoneinfo.available_timezones()), mode=SelectSelectorMode.DROPDOWN)),
        vol.Optional(CONF_BIRTH_LOCATION): LocationSelector(LocationSelectorConfig(radius=False)),
        vol.Optional(CONF_HOUSE_SYSTEM, default="placidus"): SelectSelector(SelectSelectorConfig(
            options=list(HOUSE_SYSTEMS), translation_key=CONF_HOUSE_SYSTEM)),
    })


def _validate(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    data = {**user_input, CONF_TICK_MINUTES: int(user_input[CONF_TICK_MINUTES])}
    if not data.get(CONF_BIRTH):
        for k in (CONF_BIRTH, CONF_BIRTH_LOCATION):
            data.pop(k, None)
        return data, {}
    try:
        datetime.fromisoformat(data[CONF_BIRTH])
    except (TypeError, ValueError):
        return data, {CONF_BIRTH: "invalid_birth"}
    if not data.get(CONF_BIRTH_LOCATION):
        return data, {CONF_BIRTH_LOCATION: "birth_location_required"}
    return data, {}


class SublunaryConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(title="Sublunary", data={}, options=data)
        schema = _schema(self.hass.config.time_zone)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return SublunaryOptionsFlow()


class SublunaryOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=data)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _schema(self.hass.config.time_zone), user_input or self.config_entry.options),
            errors=errors,
        )
