"""Precomputed contact timeline: ephemeris work happens once per rebuild, and
the state at any moment is a lookup. This is what the HA side schedules from.

Depth is linear in time between first contact and perfection. The Moon's speed
barely changes over a ~1 day window, so this tracks the degree-based field
closely and needs no ephemeris at lookup time.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from .ephemeris import MODERN, TRADITIONAL, Ephemeris
from .events import PTOLEMAIC, ingresses
from .moieties import LILLY_ORBS, applying_windows


@dataclass(frozen=True)
class Contact:
    body: str
    angle: float
    begin_jd: float
    perfect_jd: float
    traditional: bool

    def depth(self, jd: float) -> float:
        if not self.begin_jd <= jd < self.perfect_jd:
            return 0.0
        return (jd - self.begin_jd) / (self.perfect_jd - self.begin_jd)


@dataclass(frozen=True)
class MoonState:
    jd_tt: float
    sign: str
    sign_end_jd: float
    contacts: tuple[Contact, ...]   # active applying contacts: in-sign first, then by depth

    @property
    def dominant(self) -> Contact | None:
        return self.contacts[0] if self.contacts else None

    def crosses_sign(self, c: Contact) -> bool:
        """Is this contact reaching across the boundary *from where the Moon is now*?"""
        return c.perfect_jd > self.sign_end_jd


class Timeline:
    def __init__(self, eph: Ephemeris, jd0: float, jd1: float,
                 bodies=MODERN, orbs=LILLY_ORBS, aspects=PTOLEMAIC):
        self.jd0, self.jd1 = jd0, jd1
        pad = 3.0
        self.ingresses = ingresses(eph, "moon", jd0 - pad, jd1 + pad)
        self._ing_jd = [e.jd_tt for e in self.ingresses]
        self.contacts = sorted(
            (Contact(b, a, begin, perf, b in TRADITIONAL)
             for begin, perf, b, a in applying_windows(eph, jd0 - pad, jd1 + pad, bodies, orbs, aspects)),
            key=lambda c: c.begin_jd,
        )

    def _sign_end(self, jd: float) -> float:
        return self._ing_jd[bisect_right(self._ing_jd, jd)]

    def _sign(self, jd: float) -> str:
        return self.ingresses[bisect_right(self._ing_jd, jd) - 1].other

    def state(self, jd: float) -> MoonState:
        end = self._sign_end(jd)
        # in-sign contacts outrank boundary-crossing ones; depth breaks ties
        active = sorted((c for c in self.contacts if c.begin_jd <= jd < c.perfect_jd),
                        key=lambda c: (c.perfect_jd > end, -c.depth(jd)))
        return MoonState(jd, self._sign(jd), end, tuple(active))

    def edges(self, after_jd: float) -> list[float]:
        """Times the state changes discretely: contact begins/perfections and ingresses."""
        pts = {c.begin_jd for c in self.contacts} | {c.perfect_jd for c in self.contacts} | set(self._ing_jd)
        return sorted(p for p in pts if p > after_jd)
