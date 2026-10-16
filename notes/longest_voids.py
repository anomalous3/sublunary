"""Curiosity: extreme void-of-course moons across de440s's span, per definition."""

import sys
from pathlib import Path

from sublunary.ephemeris import MODERN, TRADITIONAL, Ephemeris
from sublunary.moieties import lilly_void
from sublunary.voc import void_of_course

eph = Ephemeris(Path(__file__).resolve().parents[1] / "data")
y0, y1 = int(sys.argv[1]), int(sys.argv[2])
best = {}
for year in range(y0, y1):
    jd0, jd1 = eph.ts.utc(year, 1, 1).tt, eph.ts.utc(year + 1, 1, 1).tt
    for name, periods in (("modern", void_of_course(eph, jd0, jd1, MODERN)),
                          ("traditional", void_of_course(eph, jd0, jd1, TRADITIONAL)),
                          ("lilly", lilly_void(eph, jd0, jd1))):
        for p in periods:
            if p.hours > best.get(name, (0,))[0]:
                la = p.last_aspect
                best[name] = (p.hours, eph.tt(p.start_jd).utc_strftime("%Y-%m-%d %H:%M"),
                              eph.tt(p.end_jd).utc_strftime("%Y-%m-%d %H:%M"), p.sign_entered,
                              f"{la.other} {int(la.angle)}" if la else "whole sign")
    print(year, {k: round(v[0], 1) for k, v in best.items()}, flush=True)
print("FINAL")
for k, v in best.items():
    print(k, v)
