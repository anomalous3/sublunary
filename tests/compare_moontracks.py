"""Compare our VoC periods against the moontracks.com fixture (traditional bodies)."""

from datetime import datetime, timezone
from pathlib import Path

from sublunary.ephemeris import MODERN, TRADITIONAL, Ephemeris
from sublunary.events import PTOLEMAIC
from sublunary.voc import void_of_course

HERE = Path(__file__).resolve().parent
NAMES = {v: k for k, v in PTOLEMAIC.items()}


def parse(s):
    return datetime.strptime(s.strip(), "%b %d, %Y %I:%M %p").replace(tzinfo=timezone.utc)


def load_fixture():
    rows = []
    for line in (HERE / "fixtures/moontracks_2026_oct_nov.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        start, asp, end, sign = (x.strip() for x in line.split("|"))
        aname, body = asp.split()
        rows.append((parse(start), NAMES[aname.lower()], body.lower(), parse(end), sign.lower()))
    return rows


def main():
    eph = Ephemeris(HERE.parent / "data")
    ref = load_fixture()
    jd0 = eph.ts.from_datetime(ref[0][3]).tt - 0.5
    jd1 = eph.ts.from_datetime(ref[-1][3]).tt + 0.5
    ours = {n: void_of_course(eph, jd0, jd1, bodies=b) for n, b in (("trad", TRADITIONAL), ("modern", MODERN))}
    worst = 0.0
    for (rs, ra, rb, re, rsign), v, m in zip(ref, ours["trad"], ours["modern"]):
        s = eph.tt(v.start_jd).utc_datetime(); e = eph.tt(v.end_jd).utc_datetime()
        ds = (s - rs).total_seconds() / 60; de = (e - re).total_seconds() / 60
        la = v.last_aspect
        same = la and la.other == rb and int(la.angle) == ra and v.sign_entered == rsign
        worst = max(worst, abs(ds), abs(de))
        mla = m.last_aspect
        mnote = "" if m.start_jd == v.start_jd else f"  modern: {mla.other} {int(mla.angle)} {eph.tt(m.start_jd).utc_strftime('%m-%d %H:%M')} ({(v.start_jd-m.start_jd)*24:+.1f}h)"
        print(f"{rs:%m-%d %H:%M} {rb:8s}{ra:4d} -> {rsign:11s} dstart={ds:+5.1f}m dend={de:+5.1f}m {'ok' if same else 'MISMATCH'}{mnote}")
    print(f"\nrows={len(ref)} ours={len(ours['trad'])}  worst |diff| = {worst:.1f} min")


if __name__ == "__main__":
    main()
