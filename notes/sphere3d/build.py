"""Bake a year of ecliptic positions (and the Moon's mean node) into the 3D sphere page."""

import json
from pathlib import Path

import numpy as np
from skyfield.framelib import ecliptic_frame

from sublunary.ephemeris import MODERN, Ephemeris
from sublunary.moieties import LILLY_ORBS, contact_distance

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STEP_H = 3
eph = Ephemeris(ROOT / "data")
jd0 = eph.ts.utc(2026, 1, 1).tt
jd = jd0 + np.arange(0, 365 * 24, STEP_H) / 24.0
t = eph.tt(jd)


def latlon(body):
    app = eph._earth.at(t).observe(eph._targets[body]).apparent()
    lat, lon, _ = app.frame_latlon(ecliptic_frame)
    return lon.degrees, lat.degrees


m_lon, m_lat = latlon("moon")
T = (jd - 2451545.0) / 36525
node = (125.0445479 - 1934.1362891 * T + 0.0020754 * T**2) % 360   # mean ascending node (Meeus)
planets = [latlon(b) for b in MODERN]
frames = [[round(float(m_lon[i]), 2), round(float(m_lat[i]), 2), round(float(node[i]), 2)]
          + [v for lo, la in planets for v in (round(float(lo[i]), 2), round(float(la[i]), 2))]
          for i in range(len(jd))]
data = {
    "start": eph.tt(jd0).utc_iso(), "stepHours": STEP_H,
    "bodies": list(MODERN), "rho": [round(contact_distance(b, LILLY_ORBS), 2) for b in MODERN],
    "orbs": [LILLY_ORBS[b] for b in MODERN],
    "frames": frames,
}
blob = json.dumps(data, separators=(",", ":"))
page = (HERE / "sphere3d.template.html").read_text().replace("/*__DATA__*/null", blob)
(HERE / "sphere3d.html").write_text(page)  # fragment for the artifact host
(ROOT / "docs" / "sublunary-sphere.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="The celestial sphere in 3D: the Moon on her tilted orbit with its nodes, '
    'Rahu and Ketu, and every planet wearing Lilly\'s orbs as caps of light, through 2026.">\n'
    + page.replace("</style>", "</style>\n</head>\n<body>", 1) + "\n</body>\n</html>\n")
print(f"{len(frames)} frames, {len(blob) / 1024:.0f} KB")
