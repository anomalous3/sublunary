"""Apparent geocentric ecliptic longitudes (true ecliptic and equinox of date) via Skyfield."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame
from skyfield.timelib import Time

# de440s covers 1849-2150 and only carries barycenters for Mars and beyond;
# the offset from planet center is far below anything that matters here.
BODY_KEYS = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars barycenter",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}

TRADITIONAL = ("sun", "mercury", "venus", "mars", "jupiter", "saturn")
MODERN = TRADITIONAL + ("uranus", "neptune", "pluto")


class Ephemeris:
    def __init__(self, data_dir: str | Path, kernel: str = "de440s.bsp"):
        load = Loader(str(data_dir), verbose=False)
        self.ts = load.timescale()
        self.eph = load(kernel)
        self._earth = self.eph["earth"]
        self._targets = {name: self.eph[key] for name, key in BODY_KEYS.items()}

    def longitude(self, body: str, t: Time) -> np.ndarray:
        apparent = self._earth.at(t).observe(self._targets[body]).apparent()
        _, lon, _ = apparent.frame_latlon(ecliptic_frame)
        return lon.degrees

    def tt(self, jd_tt) -> Time:
        return self.ts.tt_jd(jd_tt)
