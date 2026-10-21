"""A year of the Moon threading Lilly's orbs, flat versus on the sphere (projected).

Flat: contact when the longitude gap to an aspect point is within rho (sum of moieties).
Sphere: the aspect point carries latitude beta_p*cos(aspect), and contact needs the
2D distance sqrt(dlon^2 + dlat^2) within rho. Saves arrays for rendering.
"""

from pathlib import Path

import numpy as np
from skyfield.framelib import ecliptic_frame

from sublunary.ephemeris import MODERN, Ephemeris
from sublunary.moieties import LILLY_ORBS, contact_distance

HERE = Path(__file__).resolve().parent
eph = Ephemeris(HERE.parents[1] / "data")
STEP_MIN = 10
jd0 = eph.ts.utc(2026, 1, 1).tt
jd = jd0 + np.arange(0, 365 * 1440, STEP_MIN) / 1440.0
t = eph.tt(jd)


def latlon(body):
    app = eph._earth.at(t).observe(eph._targets[body]).apparent()
    lat, lon, _ = app.frame_latlon(ecliptic_frame)
    return lat.degrees, lon.degrees


m_lat, m_lon = latlon("moon")
wrap = lambda x: (x + 180) % 360 - 180
ASPECTS = (0, 60, 90, 120, 180, 240, 270, 300)

flat = np.zeros((len(MODERN), len(jd)))
sphere = np.zeros((len(MODERN), len(jd)))
p_lat_all, p_lon_all = {}, {}
for k, b in enumerate(MODERN):
    p_lat, p_lon = latlon(b)
    p_lat_all[b], p_lon_all[b] = p_lat, p_lon
    rho = contact_distance(b, LILLY_ORBS)
    for a in ASPECTS:
        dlon = wrap(m_lon - (p_lon + a))
        dlat = m_lat - p_lat * np.cos(np.radians(a))
        applying = (dlon <= 0) & (dlon > -rho)
        flat[k] = np.maximum(flat[k], np.where(applying, 1 + dlon / rho, 0))
        dist = np.hypot(dlon, dlat)
        sphere[k] = np.maximum(sphere[k], np.where((dlon <= 0) & (dist < rho), 1 - dist / rho, 0))

# eclipse seasons: the Sun within 18 deg of a lunar node (mean node, Meeus)
T = (jd - 2451545.0) / 36525
node = (125.0445479 - 1934.1362891 * T + 0.0020754 * T**2) % 360
s_lat, s_lon = latlon("sun")
node_gap = np.minimum(np.abs(wrap(s_lon - node)), np.abs(wrap(s_lon - node - 180)))

np.savez_compressed(HERE / "year.npz", jd=jd, m_lat=m_lat, m_lon=m_lon, flat=flat, sphere=sphere,
                    node_gap=node_gap, node=node, s_lon=s_lon, bodies=np.array(MODERN),
                    p_lat=np.stack([p_lat_all[b] for b in MODERN]), p_lon=np.stack([p_lon_all[b] for b in MODERN]))

f_any, s_any = flat.max(0) > 0, sphere.max(0) > 0
ghost = f_any & ~s_any               # in contact flat, void on the sphere
season = node_gap < 18
print(f"samples {len(jd)}; flat contact {f_any.mean():.1%}, sphere contact {s_any.mean():.1%}")
print(f"sphere-only void (ghost): {ghost.mean():.1%} of the year")
print(f"ghost rate in eclipse seasons {ghost[season].mean():.1%} vs outside {ghost[~season].mean():.1%}")
lat_abs = np.abs(m_lat)
for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5.3)):
    sel = (lat_abs >= lo) & (lat_abs < hi)
    print(f"  |moon lat| {lo}-{hi} deg: ghost {ghost[sel].mean():.1%} of time (n={sel.sum()})")
