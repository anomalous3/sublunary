"""Natal house cusps: Placidus, Whole Sign, Equal, Porphyry.

Inputs are a birth moment (Skyfield Time) and geographic latitude/longitude
(east positive). Everything follows from two angles: the RAMC (sidereal time at
the birthplace) and the true obliquity of the ecliptic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from skyfield.nutationlib import iau2000b_radians, mean_obliquity

SYSTEMS = ("placidus", "whole_sign", "equal", "porphyry")
POLAR_LATITUDE = 66.0  # Placidus semi-arcs break down near the polar circles


@dataclass(frozen=True)
class Houses:
    system: str              # the system actually used (Placidus falls back to Porphyry near the poles)
    cusps: tuple[float, ...]  # 12 ecliptic longitudes, cusp 1 first
    ascendant: float
    midheaven: float

    def house_of(self, lon: float) -> int:
        """1-12: the house whose cusp interval contains this longitude."""
        lon %= 360
        for i in range(12):
            a, b = self.cusps[i], self.cusps[(i + 1) % 12]
            if (lon - a) % 360 < (b - a) % 360:
                return i + 1
        return 12  # unreachable unless cusps are degenerate


def _norm(x):
    return x % 360.0


def _ra_to_lon(ra, eps):
    r = math.radians(ra)
    return _norm(math.degrees(math.atan2(math.sin(r), math.cos(r) * math.cos(eps))))


def _declination(lon, eps):
    return math.asin(math.sin(eps) * math.sin(math.radians(lon)))


def angles(t, latitude: float, longitude: float):
    """(ramc, true obliquity in radians, ascendant, midheaven)."""
    ramc = _norm(t.gast * 15.0 + longitude)
    _, deps = iau2000b_radians(t)
    eps = math.radians(mean_obliquity(t.tdb) / 3600.0) + deps
    r, phi = math.radians(ramc), math.radians(latitude)
    mc = _norm(math.degrees(math.atan2(math.sin(r), math.cos(r) * math.cos(eps))))
    asc = _norm(math.degrees(math.atan2(math.cos(r), -(math.sin(eps) * math.tan(phi) + math.cos(eps) * math.sin(r)))))
    # the ascendant is the eastern intersection: within 180 deg after the MC
    if (asc - mc) % 360 > 180:
        asc = _norm(asc + 180)
    return ramc, eps, asc, mc


def _placidus_cusp(ramc, eps, phi, fraction, above):
    """Iterate: a cusp sits where its point has covered `fraction` of its semi-arc."""
    lon = _norm(ramc + (30 if above else 210))  # rough start
    for _ in range(60):
        ad = math.degrees(math.asin(max(-1.0, min(1.0, math.tan(phi) * math.tan(_declination(lon, eps))))))
        if above:   # houses 11, 12: from the MC toward the eastern horizon, by diurnal semi-arc
            ra = ramc + fraction * (90 + ad)
        else:       # houses 2, 3: from the eastern horizon toward the IC, by nocturnal semi-arc
            ra = ramc + 180 - fraction * (90 - ad)
        new = _ra_to_lon(ra, eps)
        if abs(((new - lon) + 180) % 360 - 180) < 1e-9:
            return new
        lon = new
    return lon


def compute(t, latitude: float, longitude: float, system: str = "placidus") -> Houses:
    ramc, eps, asc, mc = angles(t, latitude, longitude)
    if system == "placidus" and abs(latitude) >= POLAR_LATITUDE:
        system = "porphyry"
    if system == "whole_sign":
        first = math.floor(asc / 30) * 30
        cusps = [_norm(first + 30 * i) for i in range(12)]
    elif system == "equal":
        cusps = [_norm(asc + 30 * i) for i in range(12)]
    elif system == "porphyry":
        ic = _norm(mc + 180)
        q1 = (ic - asc) % 360          # ASC -> IC: houses 1-3
        q2 = (asc + 180 - ic) % 360    # IC -> DSC: houses 4-6
        c = [asc, asc + q1 / 3, asc + 2 * q1 / 3, ic, ic + q2 / 3, ic + 2 * q2 / 3]
        cusps = [_norm(x) for x in c] + [_norm(x + 180) for x in c]
    elif system == "placidus":
        phi = math.radians(latitude)
        c11 = _placidus_cusp(ramc, eps, phi, 1 / 3, True)
        c12 = _placidus_cusp(ramc, eps, phi, 2 / 3, True)
        c2 = _placidus_cusp(ramc, eps, phi, 2 / 3, False)
        c3 = _placidus_cusp(ramc, eps, phi, 1 / 3, False)
        first = [asc, c2, c3, _norm(mc + 180), _norm(c11 + 180), _norm(c12 + 180)]
        cusps = first + [_norm(x + 180) for x in first]
    else:
        raise ValueError(f"unknown house system {system!r}")
    return Houses(system, tuple(cusps), asc, mc)
