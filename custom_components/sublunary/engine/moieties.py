"""Lilly's moieties: each body radiates an orb; two bodies are in contact when the
distance from an exact aspect is within the sum of their half-orbs.

The applying field is the continuous signal for the lights: per body, depth
rises 0 -> 1 from first contact to perfection, then drops to zero.

Lilly VoC (bound="sign"): void from the last perfection in a sign until the
sign ends, unless the Moon comes within moieties of an aspect before it leaves,
in which case the void ends at that first contact (or never begins).
Orb-only VoC (bound="none"): void whenever no applying contact exists at all.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict

import numpy as np

from .ephemeris import TRADITIONAL, Ephemeris
from .events import PTOLEMAIC, find_crossings, ingresses, moon_aspects, wrap180, elongation
from .voc import VoidPeriod

# Christian Astrology (1647). Sources disagree; this is configurable.
# Lilly never saw the outer planets: their 5 deg is a placeholder.
LILLY_ORBS = {
    "sun": 17.0, "moon": 12.5, "mercury": 7.0, "venus": 8.0, "mars": 7.5,
    "jupiter": 12.0, "saturn": 10.0, "uranus": 5.0, "neptune": 5.0, "pluto": 5.0,
}


def contact_distance(body: str, orbs=LILLY_ORBS) -> float:
    return (orbs["moon"] + orbs[body]) / 2.0


def _targets(aspects):
    return sorted({a for a in aspects} | {(360 - a) % 360 for a in aspects})


def applying_field(eph: Ephemeris, t, bodies=TRADITIONAL, orbs=LILLY_ORBS, aspects=PTOLEMAIC):
    """Per body: (depth array in [0,1], aspect angle array; -1 where no contact)."""
    moon = eph.longitude("moon", t)
    out = {}
    for body in bodies:
        el = moon - eph.longitude(body, t)
        thr = contact_distance(body, orbs)
        depth = np.zeros(np.shape(el))
        angle = np.full(np.shape(el), -1.0)
        for tg in _targets(aspects):
            d = wrap180(el - tg)  # negative while applying: the Moon's elongation always increases
            dep = np.where((d <= 0) & (d > -thr), 1.0 + d / thr, 0.0)
            better = dep > depth
            depth = np.where(better, dep, depth)
            angle = np.where(better, min(tg, 360 - tg), angle)
        out[body] = (depth, angle)
    return out


def dominant(field: dict):
    """Strongest applying body per sample, or None where the field is empty."""
    bodies = list(field)
    depths = np.stack([field[b][0] for b in bodies])
    idx = depths.argmax(axis=0)
    best = depths.max(axis=0)
    names = [bodies[i] if v > 0 else None for i, v in zip(np.atleast_1d(idx), np.atleast_1d(best))]
    return names, best


def applying_windows(eph, jd0, jd1, bodies=TRADITIONAL, orbs=LILLY_ORBS, aspects=PTOLEMAIC):
    """[(begin_jd, perfect_jd, body, angle)] for every applying contact perfecting in [jd0, jd1)."""
    perf = moon_aspects(eph, jd0, jd1, bodies, aspects)
    by_key = defaultdict(list)
    lead = 3.0  # contact never begins more than ~1.3 days before perfection
    for body in bodies:
        thr = contact_distance(body, orbs)
        shifted = {(tg - thr) % 360: tg for tg in _targets(aspects)}
        for jd, s, _ in find_crossings(eph, elongation(eph, "moon", body), shifted, jd0 - lead, jd1, 0.25):
            tg = shifted[s]
            by_key[(body, min(tg, 360 - tg))].append(jd)
    windows = []
    for e in perf:
        begins = by_key[(e.other, e.angle)]
        i = bisect_left(begins, e.jd_tt) - 1
        windows.append((begins[i], e.jd_tt, e.other, e.angle))
    return windows


def lilly_void(eph, jd0, jd1, bodies=TRADITIONAL, orbs=LILLY_ORBS, aspects=PTOLEMAIC, bound="sign"):
    pad = 3.0
    windows = applying_windows(eph, jd0 - pad, jd1 + pad, bodies, orbs, aspects)
    if bound == "none":
        return _gaps(windows, jd0, jd1)
    ingr = ingresses(eph, "moon", jd0 - pad, jd1)
    periods = []
    for prev, ing in zip(ingr, ingr[1:]):
        if ing.jd_tt < jd0:
            continue
        inside = [w for w in windows if prev.jd_tt < w[1] < ing.jd_tt]
        start = inside[-1][1] if inside else prev.jd_tt
        # any contact still applying when the Moon leaves this sign cuts the void short
        crossing = [w[0] for w in windows if w[1] > ing.jd_tt and w[0] < ing.jd_tt]
        end = min([ing.jd_tt] + [max(b, start) for b in crossing])
        if end > start:
            last = inside[-1] if inside else None
            periods.append(VoidPeriod(start, end, _as_event(last), ing.other))
    return periods


def _as_event(w):
    if w is None:
        return None
    from .events import Event
    return Event(w[1], "aspect", "moon", w[2], w[3], 1)


def _gaps(windows, jd0, jd1):
    spans = sorted((b, p) for b, p, _, _ in windows)
    out, cursor = [], jd0
    for b, p in spans:
        if b > cursor and cursor < jd1:
            out.append(VoidPeriod(cursor, min(b, jd1), None, ""))
        cursor = max(cursor, p)
    if cursor < jd1:
        out.append(VoidPeriod(cursor, jd1, None, ""))
    return [v for v in out if v.end_jd > max(v.start_jd, jd0)]
