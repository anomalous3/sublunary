"""Config and options flow: the refresh tick, and an optional natal chart
(birth moment, place, time zone, house system) for the Moon's natal house.
A birth place typed by name is looked up offline and fills in the map location
and time zone. VoC definitions are entities that users enable or disable."""

from __future__ import annotations

import zoneinfo
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    LocationSelector, LocationSelectorConfig,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    TextSelector, TimeSelector,
)

from . import places
from .const import (
    CONF_BIRTH, CONF_BIRTH_LOCATION, CONF_BIRTH_PLACE, CONF_BIRTH_TZ, CONF_HOUSE_SYSTEM,
    CONF_TICK_MINUTES, DEFAULT_TICK_MINUTES, DOMAIN, HOUSE_SYSTEMS,
)

NATAL_KEYS = (CONF_BIRTH, CONF_BIRTH_PLACE, CONF_BIRTH_LOCATION, CONF_BIRTH_TZ, CONF_HOUSE_SYSTEM)
# The birth moment is entered as separate fields (HA's date picker steps month by
# month, which is no way to reach a birth year) and stored as one "YYYY-MM-DD HH:MM:SS".
YEAR, MONTH, DAY, TIME = "birth_year", "birth_month", "birth_day", "birth_time"
PARTS = (YEAR, MONTH, DAY, TIME)


def _box(lo: int, hi: int) -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=lo, max=hi, step=1, mode=NumberSelectorMode.BOX))


def _split(options: dict[str, Any]) -> dict[str, Any]:
    """Stored options -> form values, with the birth moment in parts."""
    values = {k: v for k, v in options.items() if k != CONF_BIRTH}
    if options.get(CONF_BIRTH):
        b = datetime.fromisoformat(options[CONF_BIRTH])
        values |= {YEAR: b.year, MONTH: b.month, DAY: b.day, TIME: b.strftime("%H:%M:%S")}
    return values


def _schema(default_tz: str) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TICK_MINUTES, default=DEFAULT_TICK_MINUTES): NumberSelector(
            NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
        # natal chart, optional: enables the Moon's natal house
        vol.Optional(YEAR): _box(1851, 2148),
        vol.Optional(MONTH): _box(1, 12),
        vol.Optional(DAY): _box(1, 31),
        vol.Optional(TIME): TimeSelector(),
        vol.Optional(CONF_BIRTH_PLACE): TextSelector(),
        vol.Optional(CONF_BIRTH_LOCATION): LocationSelector(LocationSelectorConfig(radius=False)),
        vol.Optional(CONF_BIRTH_TZ, default=default_tz): SelectSelector(SelectSelectorConfig(
            options=sorted(zoneinfo.available_timezones()), mode=SelectSelectorMode.DROPDOWN)),
        vol.Optional(CONF_HOUSE_SYSTEM, default="placidus"): SelectSelector(SelectSelectorConfig(
            options=list(HOUSE_SYSTEMS), translation_key=CONF_HOUSE_SYSTEM)),
    })


class _NatalFlow:
    """The main form plus a place-picker step, shared by setup and options."""

    _main_step: str
    _pending: dict[str, Any]
    _matches: list[dict]

    def _current(self) -> dict[str, Any]:
        return {}

    def _finish(self, data: dict[str, Any]) -> ConfigFlowResult:
        raise NotImplementedError

    def _form(self, values: dict[str, Any] | None, errors: dict[str, str]) -> ConfigFlowResult:
        if values and values.get(CONF_BIRTH):
            values = _split(values)
        schema = _schema(self.hass.config.time_zone)
        if values:
            schema = self.add_suggested_values_to_schema(schema, values)
        return self.async_show_form(step_id=self._main_step, data_schema=schema, errors=errors)

    async def _main(self, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        if user_input is None:
            return self._form(self._current(), {})
        data = {k: v for k, v in user_input.items() if k not in PARTS}
        data[CONF_TICK_MINUTES] = int(user_input[CONF_TICK_MINUTES])
        given = [user_input.get(k) not in (None, "") for k in PARTS]
        if not any(given):
            for k in NATAL_KEYS:
                data.pop(k, None)  # no natal chart: keep none of its fields
            return self._finish(data)
        if not all(given):
            missing = next(k for k, g in zip(PARTS, given) if not g)
            return self._form(user_input, {missing: "birth_incomplete"})
        try:
            moment = datetime(int(user_input[YEAR]), int(user_input[MONTH]), int(user_input[DAY]))
            hh, mm, *ss = (int(x) for x in str(user_input[TIME]).split(":"))
            moment = moment.replace(hour=hh, minute=mm, second=ss[0] if ss else 0)
        except (TypeError, ValueError):
            return self._form(user_input, {DAY: "invalid_birth"})
        data[CONF_BIRTH] = moment.strftime("%Y-%m-%d %H:%M:%S")
        query = (data.get(CONF_BIRTH_PLACE) or "").strip()
        if query and query != self._current().get(CONF_BIRTH_PLACE):  # a new name to look up
            self._matches = await self.hass.async_add_executor_job(places.search, query)
            if not self._matches:
                return self._form(user_input, {CONF_BIRTH_PLACE: "place_not_found"})
            self._pending, self._pending_form = data, user_input
            return await self.async_step_place()
        if not data.get(CONF_BIRTH_LOCATION):
            return self._form(user_input, {CONF_BIRTH_LOCATION: "birth_location_required"})
        return self._finish(data)

    async def async_step_place(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            choice = user_input["place"]
            if choice == "map":  # back to the form, place cleared, to pick on the map
                values = {**self._pending_form, CONF_BIRTH_PLACE: ""}
                return self._form(values, {} if values.get(CONF_BIRTH_LOCATION)
                                  else {CONF_BIRTH_LOCATION: "birth_location_required"})
            m = self._matches[int(choice)]
            return self._finish({**self._pending,
                                 CONF_BIRTH_PLACE: places.label(m),
                                 CONF_BIRTH_LOCATION: {"latitude": m["latitude"], "longitude": m["longitude"]},
                                 CONF_BIRTH_TZ: m["timezone"]})
        options = [SelectOptionDict(value=str(i), label=places.label(m)) for i, m in enumerate(self._matches)]
        options.append(SelectOptionDict(value="map", label="None of these: pick it on the map"))
        return self.async_show_form(step_id="place", data_schema=vol.Schema({
            vol.Required("place", default="0"): SelectSelector(SelectSelectorConfig(
                options=options, mode=SelectSelectorMode.LIST)),
        }))


class SublunaryConfigFlow(_NatalFlow, ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _main_step = "user"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._main(user_input)

    def _finish(self, data: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(title="Sublunary", data={}, options=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return SublunaryOptionsFlow()


class SublunaryOptionsFlow(_NatalFlow, OptionsFlow):
    _main_step = "init"

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._main(user_input)

    def _current(self) -> dict[str, Any]:
        return dict(self.config_entry.options)

    def _finish(self, data: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(data=data)
