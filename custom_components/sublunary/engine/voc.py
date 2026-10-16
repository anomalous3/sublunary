"""Void-of-course Moon. Definitions are parameters, not code paths.

modern (Lynch/Morrison style): from the Moon's last Ptolemaic aspect
perfection in a sign until it enters the next sign. Bodies default to the
modern set including Uranus, Neptune and Pluto; pass TRADITIONAL for the
seven-planet version. Lilly's moiety definition comes later as a separate,
continuous model.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ephemeris import MODERN, Ephemeris
from .events import PTOLEMAIC, Event, ingresses, moon_aspects


@dataclass(frozen=True)
class VoidPeriod:
    start_jd: float
    end_jd: float
    last_aspect: Event | None   # None: no aspect perfected in the whole sign
    sign_entered: str

    @property
    def hours(self) -> float:
        return (self.end_jd - self.start_jd) * 24


def void_of_course(eph: Ephemeris, jd0, jd1, bodies=MODERN, aspects=PTOLEMAIC) -> list[VoidPeriod]:
    """Void periods whose ingress falls in [jd0, jd1)."""
    pad = 3.0  # the Moon spends at most ~2.7 days per sign
    ingr = ingresses(eph, "moon", jd0 - pad, jd1)
    asp = moon_aspects(eph, jd0 - pad, jd1, bodies, aspects)
    periods = []
    for prev, ing in zip(ingr, ingr[1:]):
        if ing.jd_tt < jd0:
            continue
        inside = [a for a in asp if prev.jd_tt < a.jd_tt < ing.jd_tt]
        last = inside[-1] if inside else None
        start = last.jd_tt if last else prev.jd_tt
        periods.append(VoidPeriod(start, ing.jd_tt, last, ing.other))
    return periods
