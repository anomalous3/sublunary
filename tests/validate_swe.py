"""Cross-check Skyfield-found events against Swiss Ephemeris (Moshier, no data files).

At each event time, measure how far the swisseph angle is from the target,
then convert that residual into seconds using swisseph's own speeds.
Run: .venv/bin/python3 -m tests.validate_swe [year]
"""

import sys
from pathlib import Path

import numpy as np
import swisseph as swe

from sublunary.ephemeris import MODERN, Ephemeris
from sublunary.events import ingresses, lunar_phases, moon_aspects, wrap180
from sublunary.voc import void_of_course

SWE_ID = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS,
    "mars": swe.MARS, "jupiter": swe.JUPITER, "saturn": swe.SATURN,
    "uranus": swe.URANUS, "neptune": swe.NEPTUNE, "pluto": swe.PLUTO,
}
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


def lon_speed(body, jd_tt):
    xx, _ = swe.calc(jd_tt, SWE_ID[body], FLAGS)  # TT input sidesteps Delta-T differences
    return xx[0], xx[3]


def residual_seconds(ev):
    lm, sm = lon_speed(ev.body, ev.jd_tt)
    if ev.kind == "ingress":
        val, rate = lm, sm
    else:
        other = "sun" if ev.kind == "phase" else ev.other
        lo, so = lon_speed(other, ev.jd_tt)
        val, rate = lm - lo, sm - so
    targets = [ev.angle] if ev.kind != "aspect" else [ev.angle, -ev.angle]
    resid = min((wrap180(val - t) for t in targets), key=abs)
    return float(resid / rate * 86400)


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    eph = Ephemeris(Path(__file__).resolve().parents[1] / "data")
    jd0 = eph.ts.utc(year, 1, 1).tt
    jd1 = eph.ts.utc(year + 1, 1, 1).tt

    groups = {
        "moon aspects": moon_aspects(eph, jd0, jd1, MODERN),
        "moon ingresses": ingresses(eph, "moon", jd0, jd1),
        "phases": lunar_phases(eph, jd0, jd1),
        "planet ingresses": [e for b in MODERN for e in ingresses(eph, b, jd0, jd1)],
    }
    for name, evs in groups.items():
        r = np.abs([residual_seconds(e) for e in evs])
        print(f"{name:18s} n={len(evs):4d}  median={np.median(r):6.2f}s  max={r.max():6.2f}s")

    voids = void_of_course(eph, jd0, jd1)
    print(f"\nVoC periods {year}: {len(voids)}, mean {np.mean([v.hours for v in voids]):.1f}h, "
          f"max {max(v.hours for v in voids):.1f}h")
    print("first five (UTC):")
    for v in voids[:5]:
        la = v.last_aspect
        what = f"{la.other} {int(la.angle)}" if la else "(no aspect in sign)"
        s = eph.tt(v.start_jd).utc_strftime("%Y-%m-%d %H:%M")
        e = eph.tt(v.end_jd).utc_strftime("%Y-%m-%d %H:%M")
        print(f"  {s} -> {e}  ({v.hours:5.1f}h)  last: {what:16s} enters {v.sign_entered}")


if __name__ == "__main__":
    main()
