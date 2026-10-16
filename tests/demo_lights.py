"""Render the warm/cool + Lilly-brightness template as text over a span of hours."""

import sys
from pathlib import Path

from sublunary.ephemeris import Ephemeris
from sublunary.timeline import Timeline

IN_SIGN, ACROSS = (0.60, 1.00), (0.15, 0.25)


def light(state):
    c = state.dominant
    if c is None:
        return "off", 0.0, None
    lo, hi = ACROSS if state.crosses_sign(c) else IN_SIGN
    return ("warm" if c.traditional else "cool"), lo + (hi - lo) * c.depth(state.jd_tt), c


def main():
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    eph = Ephemeris(Path(__file__).resolve().parents[1] / "data")
    now = eph.ts.now().tt
    tl = Timeline(eph, now - 1, now + hours / 24 + 1)
    for h in range(0, hours, 2):
        jd = now + h / 24
        st = tl.state(jd)
        tone, bri, c = light(st)
        what = f"{c.body} {int(c.angle)}{' (across)' if st.crosses_sign(c) else ''}" if c else ""
        print(f"{eph.tt(jd).utc_strftime('%m-%d %H:%M')}  {st.sign:11s} {tone:4s} {bri:4.0%} {'#' * int(bri * 20):20s} {what}")


if __name__ == "__main__":
    main()
