"""Cross-check house cusps against Swiss Ephemeris over random births and latitudes."""

import random
from pathlib import Path

import swisseph as swe

from sublunary import houses
from sublunary.ephemeris import Ephemeris

CODES = {"placidus": b"P", "whole_sign": b"W", "equal": b"E", "porphyry": b"O"}


def diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def main():
    eph = Ephemeris(Path(__file__).resolve().parents[1] / "data")
    rng = random.Random(7)
    worst = {k: 0.0 for k in CODES}
    for _ in range(400):
        y, mo, d = rng.randint(1900, 2100), rng.randint(1, 12), rng.randint(1, 28)
        h, mi = rng.randint(0, 23), rng.randint(0, 59)
        lat, lon = rng.uniform(-65, 65), rng.uniform(-180, 180)
        t = eph.ts.utc(y, mo, d, h, mi)
        for system, code in CODES.items():
            ours = houses.compute(t, lat, lon, system)
            cusps, ascmc = swe.houses(t.ut1, lat, lon, code)
            worst[system] = max(worst[system], max(diff(a, b) for a, b in zip(ours.cusps, cusps)),
                                diff(ours.ascendant, ascmc[0]), diff(ours.midheaven, ascmc[1]))
    for system, w in worst.items():
        print(f"{system:11s} worst cusp/angle difference over 400 charts: {w * 3600:7.2f} arcsec")
    polar = houses.compute(eph.ts.utc(2000, 1, 1, 12), 70.0, 20.0, "placidus")
    print("Placidus at 70N falls back to:", polar.system)


if __name__ == "__main__":
    main()
