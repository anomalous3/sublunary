"""Sublunary: astrological events as Home Assistant sensors."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SublunaryCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SET_CLOCK_SCHEMA = vol.Schema({
    vol.Optional("start"): cv.datetime,
    vol.Optional("speed", default=1.0): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=100000)),
})

type SublunaryConfigEntry = ConfigEntry[SublunaryCoordinator]


def _coordinator(hass: HomeAssistant) -> SublunaryCoordinator:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError("Sublunary is not set up")
    return entries[0].runtime_data


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def set_clock(call: ServiceCall) -> None:
        start = call.data.get("start")
        if start is not None:
            start = dt_util.as_utc(start)
            if not 1851 <= start.year <= 2148:
                raise ServiceValidationError("start must be between 1851 and 2148 (ephemeris range)")
        await _coordinator(hass).async_set_clock(start, call.data["speed"])

    async def reset_clock(call: ServiceCall) -> None:
        await _coordinator(hass).async_reset_clock()

    hass.services.async_register(DOMAIN, "set_clock", set_clock, SET_CLOCK_SCHEMA)
    hass.services.async_register(DOMAIN, "reset_clock", reset_clock)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SublunaryConfigEntry) -> bool:
    coordinator = SublunaryCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SublunaryConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return unloaded


async def _async_reload(hass: HomeAssistant, entry: SublunaryConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
