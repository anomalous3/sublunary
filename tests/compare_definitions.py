"""All VoC definitions side by side, plus the applying field around a moment."""

import sys
from pathlib import Path

import numpy as np

from sublunary.ephemeris import MODERN, TRADITIONAL, Ephemeris
from sublunary.moieties import applying_field, dominant, lilly_void
from sublunary.voc import void_of_course


def total_hours(periods):
    return sum(p.hours for p in periods)


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    eph = Ephemeris(Path(__file__).resolve().parents[1] / "data")
    jd0, jd1 = eph.ts.utc(year, 1, 1).tt, eph.ts.utc(year + 1, 1, 1).tt
    defs = {
        "modern (Lynch, +outers)": void_of_course(eph, jd0, jd1, MODERN),
        "traditional (7 bodies)": void_of_course(eph, jd0, jd1, TRADITIONAL),
        "Lilly moieties, sign": lilly_void(eph, jd0, jd1),
        "Lilly moieties, no sign": lilly_void(eph, jd0, jd1, bound="none"),
    }
    print(f"{year}: definition                 periods   void hours   % of year")
    for name, p in defs.items():
        h = total_hours(p)
        print(f"   {name:26s} {len(p):6d} {h:11.0f} {100*h/(24*(jd1-jd0)):9.1f}%")

    trad, lil = defs["traditional (7 bodies)"], defs["Lilly moieties, sign"]
    lil_by_end = {round(p.end_jd, 3) for p in lil}
    cut = [p for p in trad if not any(abs(l.start_jd - p.start_jd) < 1e-6 and abs(l.end_jd - p.end_jd) < 1e-6 for l in lil)]
    print(f"\ntraditional voids Lilly shortens or cancels: {len(cut)} of {len(trad)}")
    for p in cut[:4]:
        l = next((l for l in lil if abs(l.start_jd - p.start_jd) < 1e-6), None)
        s = eph.tt(p.start_jd).utc_strftime("%m-%d %H:%M"); e = eph.tt(p.end_jd).utc_strftime("%m-%d %H:%M")
        note = f"Lilly ends {eph.tt(l.end_jd).utc_strftime('%m-%d %H:%M')}" if l else "Lilly: not void at all"
        print(f"   trad {s} -> {e} ({p.hours:4.1f}h, enters {p.sign_entered}); {note}")

    now = eph.ts.now()
    t = eph.tt(now.tt + np.arange(-6, 19, 2) / 24)
    names, depth = dominant(applying_field(eph, t, MODERN))
    print("\napplying field around now (UTC), dominant body:")
    for ti, n, d in zip(t, names, depth):
        bar = "#" * int(round(d * 20))
        print(f"   {ti.utc_strftime('%m-%d %H:%M')}  {(n or '-'):8s} {d:4.2f} {bar}")


if __name__ == "__main__":
    main()
