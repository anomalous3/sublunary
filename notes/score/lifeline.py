"""A whole life's slow transits: the quietest stretches and the loudest moments, against random births as a control.

Usage: python -m notes.score.lifeline  (chart at top). Loudness = sum of depth over aspects in working orbs.
"""

import base64, json, struct
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import numpy as np
from skyfield.framelib import ecliptic_frame

from sublunary.ephemeris import Ephemeris
from sublunary import houses as H

# the chart comes from the gitignored first_chart.json: {date, time, lat, lon, tz}
_c = json.load(open(Path(__file__).resolve().parent / "first_chart.json"))
_u = datetime.fromisoformat(f"{_c['date']}T{_c['time']}").replace(tzinfo=ZoneInfo(_c["tz"])).astimezone(timezone.utc)
BIRTH = (_u.year, _u.month, _u.day, _u.hour, _u.minute); LAT, LON = _c["lat"], _c["lon"]
YEARS = 90; N_CONTROL = 400
HERE = Path(__file__).resolve().parent
eph = Ephemeris(HERE.parents[1] / "data")
PLANETS = ["jupiter", "saturn", "uranus", "neptune", "pluto"]
ORB = {"jupiter": 3, "saturn": 3, "uranus": 2, "neptune": 2, "pluto": 2, "chiron": 2}
ANG = np.array([0, 60, 90, 120, 180, 240, 270, 300.0])
NAMES = {0: "conjunct", 60: "sextile", 90: "square", 120: "trine", 180: "opposite"}


def lon(body, t):
    return eph._earth.at(t).observe(eph._targets[body]).apparent().frame_latlon(ecliptic_frame)[1].degrees


D = json.load(open(HERE / "bodies.json"))
raw = base64.b64decode(D["bodies"]["chiron"])
chi = np.unwrap(np.array(struct.unpack(f"<{len(raw)//2}H", raw)) * D["scale"], period=360)
chi0 = eph.ts.utc(1900, 1, 1).tt


def chiron(jd):
    return np.interp(jd, chi0 + np.arange(len(chi)) * 5.0, chi) % 360


def sky(jd):
    t = eph.tt(jd)
    out = {b: lon(b, t) for b in PLANETS}
    out["chiron"] = chiron(jd)
    return out


def natal_points(tjd, lat, lonE):
    t = eph.tt(np.array([tjd]))
    pts = {b: float(lon(b, t)[0]) for b in "sun moon mercury venus mars jupiter saturn uranus neptune pluto".split()}
    pts["chiron"] = float(chiron(np.array([tjd]))[0])
    tt = eph.ts.tt_jd(tjd)
    h = H.compute(tt, lat, lonE, "placidus")
    pts["asc"], pts["mc"] = h.ascendant, h.midheaven
    return pts


def loudness(pts, S, bodies):
    """Per day: summed depth, count in orb, and (for detail) the depth array per (body, point, angle)."""
    total = 0
    count = 0
    for b in bodies:
        for q, v in pts.items():
            sd = np.abs(((S[b][:, None] - v - ANG) + 180) % 360 - 180)
            d = np.clip(1 - sd / ORB[b], 0, None)
            total = total + d.sum(1)
            count = count + (d > 0).sum(1)
    return total, count


def smooth(x, w=30):
    return np.convolve(x, np.ones(w) / w, mode="same")


t0 = eph.ts.utc(*BIRTH).tt
jd = t0 + np.arange(0, YEARS * 365.25)
print("computing sky", len(jd), "days", flush=True)
S = sky(jd)
pts = natal_points(t0, LAT, LON)
age = (jd - t0) / 365.25
OUT = ["saturn", "uranus", "neptune", "pluto"]


def runs(mask):
    edges = np.flatnonzero(np.diff(np.r_[0, mask.astype(int), 0]))
    return [(a, b) for a, b in zip(edges[::2], edges[1::2])]


def date(i):
    return eph.tt(float(jd[i])).utc_strftime("%Y-%m-%d")


for label, bodies in (("Saturn to Pluto", OUT), ("Jupiter to Pluto, Chiron", PLANETS + ["chiron"])):
    tot, cnt = loudness(pts, S, bodies)
    print(f"\n=== {label} ===")
    q = sorted(runs(cnt == 0), key=lambda r: r[0] - r[1])[:5]
    print("longest silences (nothing in orb):")
    for a, b in q:
        print(f"  {b-a:5d} days  age {age[a]:5.1f}-{age[b-1]:5.1f}  {date(a)} to {date(b-1)}")
    print("share of life with nothing in orb:", round(float((cnt == 0).mean()) * 100, 1), "%")
    st = smooth(tot)
    order = np.argsort(-st)
    picks = []
    for i in order:
        if all(abs(i - p) > 365 for p in picks):
            picks.append(int(i))
        if len(picks) == 6:
            break
    print("loudest moments (30-day mean of summed depth):")
    for i in picks:
        print(f"  {st[i]:5.2f}  age {age[i]:5.1f}  {date(i)}  ({int(cnt[i])} in orb)")
    today = int(np.searchsorted(jd, eph.ts.now().tt))
    print(f"today: {st[today]:.2f}, percentile of life {float((st < st[today]).mean()) * 100:.1f}, {int(cnt[today])} in orb")
    by5 = [float(st[(age >= a) & (age < a + 5)].mean()) for a in range(0, 90, 5)]
    print("mean loudness by 5-year age band:", " ".join(f"{a}:{v:.2f}" for a, v in zip(range(0, 90, 5), by5)))

# who's in the loudest moment?
tot, cnt = loudness(pts, S, PLANETS + ["chiron"])
st = smooth(tot); i = int(np.argmax(st))
print("\nin the loudest moment,", date(i), ":")
rows = []
for b in PLANETS + ["chiron"]:
    for q, v in pts.items():
        for a in ANG:
            sd = abs((S[b][i] - v - a + 180) % 360 - 180)
            if sd < ORB[b]:
                rows.append((sd, b, NAMES[min(a, 360 - a)], q))
for sd, b, n, q in sorted(rows):
    print(f"  {b} {n} {q} {sd:.2f}")

# the control: is this chart's midlife unusual, or everyone's?
print("\ncontrol:", N_CONTROL, "random births 1950-2000, 90-year window each", flush=True)
rng = np.random.default_rng(7)
span0 = eph.ts.utc(1950, 1, 1).tt
long_jd = span0 + np.arange(0, (50 + YEARS) * 365.25)
LS = sky(long_jd)
res_peak_age, res_band, res_my = [], [], []
bodies = PLANETS + ["chiron"]
for k in range(N_CONTROL):
    off = int(rng.integers(0, int(50 * 365.25)))
    tj = long_jd[off]
    lat = float(rng.uniform(-40, 55))
    p = natal_points(float(tj), lat, float(rng.uniform(-180, 180)))
    Sx = {b: LS[b][off:off + len(jd)] for b in bodies}
    t, _ = loudness(p, Sx, bodies)
    s = smooth(t)
    res_peak_age.append(np.argmax(s) / 365.25)
    res_band.append([float(s[(age >= a) & (age < a + 5)].mean()) for a in range(0, 90, 5)])
    if k % 100 == 0:
        print(" ", k, flush=True)
res_band = np.array(res_band)
print("control mean loudness by 5-year band:", " ".join(f"{a}:{v:.2f}" for a, v in zip(range(0, 90, 5), res_band.mean(0))))
mine = np.array([float(st[(age >= a) & (age < a + 5)].mean()) for a in range(0, 90, 5)])
pct = [(res_band[:, j] < mine[j]).mean() * 100 for j in range(18)]
print("this chart's percentile vs control, by band:", " ".join(f"{a}:{p:.0f}" for a, p in zip(range(0, 90, 5), pct)))
print("control peak age: median", round(float(np.median(res_peak_age)), 1), "IQR", np.round(np.percentile(res_peak_age, [25, 75]), 1))
print("this chart's peak age:", round(float(age[i]), 1), "; percentile of peak height vs control's:", end=" ")
print("done")
