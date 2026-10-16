"""Sublunary: astrological events as Home Assistant sensors."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SublunaryCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type SublunaryConfigEntry = ConfigEntry[SublunaryCoordinator]


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
