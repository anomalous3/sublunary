"""Event finding: every event here is an angle function of time crossing a target.

Aspects are the Moon-planet elongation crossing 0/60/90/...; ingresses are a
longitude crossing a multiple of 30; phases are the Moon-Sun elongation
crossing 0/90/180/270. One vectorized bisection serves all of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable

import numpy as np

from .ephemeris import Ephemeris

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
PTOLEMAIC = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}
PHASES = {0: "new", 90: "first_quarter", 180: "full", 270: "last_quarter"}


@dataclass(frozen=True)
class Event:
    jd_tt: float
    kind: str           # "aspect" | "ingress" | "phase"
    body: str
    other: str | None   # aspected body, sign entered, or phase name
    angle: float        # target angle that was crossed
    direction: int      # +1 increasing through target, -1 decreasing (retrograde ingress)

    def utc(self, eph: Ephemeris) -> datetime:
        return eph.tt(self.jd_tt).utc_datetime()


def wrap180(x):
    return (np.asarray(x) + 180.0) % 360.0 - 180.0


def find_crossings(
    eph: Ephemeris,
    f: Callable,
    targets: Iterable[float],
    jd0: float,
    jd1: float,
    step_days: float,
    tol_seconds: float = 0.5,
):
    """Return (jd_tt, target, direction) for each time f(t) crosses a target in [jd0, jd1).

    f maps a Skyfield Time array to degrees. Sampling must be fine enough that a
    given target is crossed at most once per step.
    """
    jd = np.arange(jd0, jd1 + step_days, step_days)
    vals = f(eph.tt(jd))
    lo_l, hi_l, tg_l, dir_l = [], [], [], []
    for target in targets:
        d = wrap180(vals - target)
        a, b = d[:-1], d[1:]
        # sign change that isn't the +-180 wraparound
        idx = np.nonzero(((a < 0) != (b < 0)) & (np.abs(b - a) < 180))[0]
        lo_l.append(jd[idx]); hi_l.append(jd[idx + 1])
        tg_l.append(np.full(idx.size, float(target)))
        dir_l.append(np.where(b[idx] > a[idx], 1, -1))
    lo, hi = np.concatenate(lo_l), np.concatenate(hi_l)
    tg, dirs = np.concatenate(tg_l), np.concatenate(dir_l)
    if lo.size == 0:
        return []
    neg_lo = dirs > 0  # f - target is negative at lo when increasing
    tol = tol_seconds / 86400.0
    while np.max(hi - lo) > tol:
        mid = (lo + hi) / 2
        dm = wrap180(f(eph.tt(mid)) - tg)
        at_lo_side = (dm < 0) == neg_lo
        lo = np.where(at_lo_side, mid, lo)
        hi = np.where(at_lo_side, hi, mid)
    t = (lo + hi) / 2
    keep = (t >= jd0) & (t < jd1)
    out = sorted(zip(t[keep], tg[keep], dirs[keep]))
    return [(float(j), float(g), int(s)) for j, g, s in out]


def elongation(eph: Ephemeris, a: str, b: str) -> Callable:
    return lambda t: eph.longitude(a, t) - eph.longitude(b, t)


def moon_aspects(eph, jd0, jd1, bodies, aspects=PTOLEMAIC, step_days=0.25) -> list[Event]:
    """Perfections of Moon aspects. The Moon outruns every planet, so each
    elongation increases monotonically and 6h sampling is safe."""
    targets = sorted({a for a in aspects} | {(360 - a) % 360 for a in aspects})
    events = []
    for body in bodies:
        for jd, tg, s in find_crossings(eph, elongation(eph, "moon", body), targets, jd0, jd1, step_days):
            angle = min(tg, 360 - tg)
            events.append(Event(jd, "aspect", "moon", body, angle, s))
    return sorted(events, key=lambda e: e.jd_tt)


def ingresses(eph, body, jd0, jd1, step_days=None) -> list[Event]:
    if step_days is None:
        step_days = 0.25 if body == "moon" else 1.0
    f = lambda t: eph.longitude(body, t)
    out = []
    for jd, tg, s in find_crossings(eph, f, range(0, 360, 30), jd0, jd1, step_days):
        idx = int(round(tg / 30)) % 12
        sign = SIGNS[idx] if s > 0 else SIGNS[(idx - 1) % 12]
        out.append(Event(jd, "ingress", body, sign, tg, s))
    return out


def lunar_phases(eph, jd0, jd1, step_days=0.5) -> list[Event]:
    return [
        Event(jd, "phase", "moon", PHASES[int(tg)], tg, s)
        for jd, tg, s in find_crossings(eph, elongation(eph, "moon", "sun"), PHASES, jd0, jd1, step_days)
    ]
