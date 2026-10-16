"""Moon sign, phase, and dominant applying contact."""

from __future__ import annotations

from dataclasses import asdict

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SublunaryConfigEntry
from .const import PHASE_NAMES
from .engine.events import SIGNS
from .entity import SublunaryEntity

BODIES = ("sun", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")


async def async_setup_entry(hass: HomeAssistant, entry: SublunaryConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    c = entry.runtime_data
    async_add_entities([MoonSignSensor(c, "moon_sign"), MoonPhaseSensor(c, "moon_phase"),
                        DominantContactSensor(c, "dominant_contact")])


class MoonSignSensor(SublunaryEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(SIGNS)
    _attr_icon = "mdi:zodiac-aries"

    @property
    def native_value(self):
        return self.coordinator.data.sign

    @property
    def extra_state_attributes(self):
        return {"next_ingress": self.coordinator.data.next_ingress.isoformat()}


class MoonPhaseSensor(SublunaryEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(PHASE_NAMES)
    _attr_icon = "mdi:moon-waxing-crescent"

    @property
    def native_value(self):
        return self.coordinator.data.phase

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {
            "illumination": d.illumination,
            "elongation": d.elongation,
            "next_phase": d.next_phase,
            "next_phase_at": d.next_phase_at.isoformat(),
        }


class DominantContactSensor(SublunaryEntity, SensorEntity):
    """State is the body the Moon is most strongly applying to (in-sign first), or none."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["none", *BODIES]
    _attr_icon = "mdi:orbit"

    @property
    def native_value(self):
        dom = self.coordinator.data.dominant
        return dom.body if dom else "none"

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        dom = d.dominant

        def plain(ci):
            out = asdict(ci)
            out["begins"], out["perfects"] = ci.begins.isoformat(), ci.perfects.isoformat()
            return out

        attrs = {"contacts": [plain(c) for c in d.contacts]}
        if dom:
            attrs |= {k: v for k, v in plain(dom).items() if k != "body"}
        return attrs
