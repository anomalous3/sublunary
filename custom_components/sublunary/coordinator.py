"""Coordinator: owns the ephemeris and timeline, publishes a Snapshot.

Ephemeris work (kernel load, timeline rebuild) runs in the executor. State
refreshes on a short tick for continuous depth, and exactly at each discrete
edge (contact begin/perfection, ingress, void start/end).

Time can be simulated: sim = sim_anchor + (real - real_anchor) * speed. Edges
are computed in sim time and mapped back to real time for scheduling.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEFINITIONS, CONF_TICK_MINUTES, DEFAULT_DEFINITIONS, DEFAULT_TICK_MINUTES,
    DOMAIN, HORIZON_DAYS, PHASE_NAMES, REBUILD_MARGIN_DAYS,
)
from .engine.ephemeris import MODERN, TRADITIONAL, Ephemeris
from .engine.events import PTOLEMAIC, lunar_phases
from .engine.moieties import lilly_void
from .engine.timeline import Timeline
from .engine.voc import void_of_course

_LOGGER = logging.getLogger(__name__)

# de440s spans 1849-12-26 .. 2150-01-22; keep the timeline's padding inside it
SIM_MIN = datetime(1851, 1, 1, tzinfo=timezone.utc)
SIM_MAX = datetime(2149, 12, 1, tzinfo=timezone.utc)


@dataclass
class ContactInfo:
    body: str
    aspect: str
    depth: float
    in_sign: bool
    tone: str           # "warm" (traditional body) | "cool" (outer planet)
    begins: datetime
    perfects: datetime


@dataclass
class VoidInfo:
    active: bool
    start: datetime | None = None
    end: datetime | None = None
    last_aspect: str | None = None
    next_start: datetime | None = None
    next_end: datetime | None = None


@dataclass
class Snapshot:
    now: datetime
    simulated: bool
    speed: float
    sign: str
    next_ingress: datetime
    elongation: float
    illumination: float
    phase: str
    next_phase: str
    next_phase_at: datetime
    dominant: ContactInfo | None
    contacts: list[ContactInfo] = field(default_factory=list)
    voids: dict[str, VoidInfo] = field(default_factory=dict)
    paused: bool = False


class SublunaryCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        tick = entry.options.get(CONF_TICK_MINUTES, DEFAULT_TICK_MINUTES)
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(minutes=tick))
        self.definitions: list[str] = entry.options.get(CONF_DEFINITIONS, DEFAULT_DEFINITIONS)
        self._data_dir = hass.config.path(DOMAIN)
        self._eph: Ephemeris | None = None
        self._timeline: Timeline | None = None
        self._periods: dict[str, list] = {}
        self._phases: list = []
        self._built_from = 0.0
        self._built_until = 0.0
        self._unsub_edge = None
        self._base_tick = timedelta(minutes=tick)
        self._sim_anchor: datetime | None = None
        self._real_anchor: datetime | None = None
        self.speed = 1.0
        self._paused = False

    # --- clock -----------------------------------------------------------

    @property
    def simulated(self) -> bool:
        return self._sim_anchor is not None

    def sim_now(self) -> datetime:
        real = dt_util.utcnow()
        if self._sim_anchor is None:
            return real
        if self._paused:
            return self._sim_anchor
        sim = self._sim_anchor + (real - self._real_anchor) * self.speed
        if not SIM_MIN <= sim <= SIM_MAX:
            # a fast clock stops at the ephemeris edge rather than running off it
            sim = min(max(sim, SIM_MIN), SIM_MAX)
            self._sim_anchor, self._real_anchor, self._paused = sim, real, True
            _LOGGER.warning("Sublunary simulated clock reached the ephemeris edge and paused at %s", sim)
        return sim

    def to_real(self, sim_dt: datetime) -> datetime | None:
        if self._sim_anchor is None:
            return sim_dt
        if self._paused:
            return None
        return self._real_anchor + (sim_dt - self._sim_anchor) / self.speed

    async def async_set_clock(self, start: datetime | None, speed: float) -> None:
        sim = start or self.sim_now()  # no start: continue from current sim time
        self._real_anchor, self._sim_anchor, self.speed = dt_util.utcnow(), sim, speed
        self._paused = False
        self.update_interval = max(timedelta(seconds=5), self._base_tick / speed)
        await self.async_refresh()

    async def async_reset_clock(self) -> None:
        self._sim_anchor = self._real_anchor = None
        self.speed = 1.0
        self._paused = False
        self.update_interval = self._base_tick
        await self.async_refresh()

    # --- refresh ---------------------------------------------------------

    async def _async_update_data(self) -> Snapshot:
        snap, next_edge = await self.hass.async_add_executor_job(self._compute, self.sim_now())
        self._schedule_edge(self.to_real(next_edge) if next_edge else None)
        snap.paused = self._paused
        return snap

    # --- executor side -------------------------------------------------

    def _rebuild(self, now: float) -> None:
        eph = self._eph
        jd0, jd1 = now - 1, now + HORIZON_DAYS
        self._timeline = Timeline(eph, jd0, jd1, MODERN)
        builders = {
            "modern": lambda: void_of_course(eph, jd0, jd1, MODERN),
            "traditional": lambda: void_of_course(eph, jd0, jd1, TRADITIONAL),
            "lilly": lambda: lilly_void(eph, jd0, jd1),
            "lilly_unbounded": lambda: lilly_void(eph, jd0, jd1, bound="none"),
        }
        self._periods = {d: builders[d]() for d in self.definitions}
        self._phases = lunar_phases(eph, jd0, jd1)
        self._built_from, self._built_until = jd0, jd1
        _LOGGER.debug("Sublunary timeline rebuilt through JD %.2f", jd1)

    def _compute(self, now_utc: datetime) -> tuple[Snapshot, datetime | None]:
        if self._eph is None:
            self._eph = Ephemeris(self._data_dir)  # downloads de440s on first run
        eph = self._eph
        to_dt = lambda jd: eph.tt(jd).utc_datetime()
        now = eph.ts.from_datetime(now_utc).tt
        if (self._timeline is None or now > self._built_until - REBUILD_MARGIN_DAYS
                or now < self._built_from + 0.5):  # clock jumped backward
            self._rebuild(now)

        st = self._timeline.state(now)
        contacts = [
            ContactInfo(
                body=c.body,
                aspect=PTOLEMAIC[int(c.angle)],
                depth=round(float(c.depth(now)), 4),
                in_sign=not st.crosses_sign(c),
                tone="warm" if c.traditional else "cool",
                begins=to_dt(c.begin_jd),
                perfects=to_dt(c.perfect_jd),
            )
            for c in st.contacts
        ]

        t = eph.tt(now)
        el = float((eph.longitude("moon", t) - eph.longitude("sun", t)) % 360)
        phase = PHASE_NAMES[int(((el + 22.5) % 360) // 45)]
        nxt = next(p for p in self._phases if p.jd_tt > now)

        voids = {}
        edges = [e for e in self._timeline.edges(now)[:1]]
        for name, periods in self._periods.items():
            cur = next((p for p in periods if p.start_jd <= now < p.end_jd), None)
            upcoming = next((p for p in periods if p.start_jd > now), None)
            la = cur.last_aspect if cur else None
            voids[name] = VoidInfo(
                active=cur is not None,
                start=to_dt(cur.start_jd) if cur else None,
                end=to_dt(cur.end_jd) if cur else None,
                last_aspect=f"{PTOLEMAIC[int(la.angle)]} {la.other}" if la else None,
                next_start=to_dt(upcoming.start_jd) if upcoming else None,
                next_end=to_dt(upcoming.end_jd) if upcoming else None,
            )
            edges += [cur.end_jd] if cur else []
            edges += [upcoming.start_jd] if upcoming else []

        snap = Snapshot(
            now=now_utc,
            simulated=self.simulated,
            speed=self.speed,
            sign=st.sign,
            next_ingress=to_dt(st.sign_end_jd),
            elongation=round(el, 3),
            illumination=round((1 - math.cos(math.radians(el))) / 2, 4),
            phase=phase,
            next_phase=nxt.other,
            next_phase_at=to_dt(nxt.jd_tt),
            dominant=contacts[0] if contacts else None,
            contacts=contacts,
            voids=voids,
        )
        return snap, (to_dt(min(edges)) if edges else None)

    # --- event loop side -----------------------------------------------

    def _schedule_edge(self, when: datetime | None) -> None:
        if self._unsub_edge:
            self._unsub_edge()
            self._unsub_edge = None
        if when is not None:
            # never in the past: a past edge would refresh, reschedule, and spin
            when = max(when + timedelta(seconds=1), dt_util.utcnow() + timedelta(seconds=1))
            self._unsub_edge = async_track_point_in_utc_time(self.hass, self._on_edge, when)

    async def _on_edge(self, _now: datetime) -> None:
        self._unsub_edge = None
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        if self._unsub_edge:
            self._unsub_edge()
            self._unsub_edge = None
        await super().async_shutdown()
