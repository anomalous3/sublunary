"""One void-of-course binary sensor per enabled definition."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SublunaryConfigEntry
from .entity import SublunaryEntity


async def async_setup_entry(hass: HomeAssistant, entry: SublunaryConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities(VoidOfCourseSensor(c, d) for d in c.definitions)


class VoidOfCourseSensor(SublunaryEntity, BinarySensorEntity):
    _attr_icon = "mdi:moon-full"

    def __init__(self, coordinator, definition: str) -> None:
        super().__init__(coordinator, f"void_of_course_{definition}")
        self._definition = definition

    @property
    def _info(self):
        return self.coordinator.data.voids[self._definition]

    @property
    def is_on(self) -> bool:
        return self._info.active

    @property
    def extra_state_attributes(self):
        v = self._info
        iso = lambda x: x.isoformat() if x else None
        return {
            "definition": self._definition,
            "start": iso(v.start), "end": iso(v.end), "last_aspect": v.last_aspect,
            "next_start": iso(v.next_start), "next_end": iso(v.next_end),
        }
