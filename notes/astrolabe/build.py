"""Run the engine over a lunar month and bake the frames into astrolabe.html."""

import json
from pathlib import Path

import numpy as np

from sublunary.ephemeris import MODERN, TRADITIONAL, Ephemeris
from sublunary.events import SIGNS
from sublunary.moieties import LILLY_ORBS, contact_distance, lilly_void
from sublunary.timeline import Timeline
from sublunary.voc import void_of_course

HERE = Path(__file__).resolve().parent
START = (2026, 10, 14)
DAYS, STEP_MIN = 28, 30

eph = Ephemeris(HERE.parents[1] / "data")
jd0 = eph.ts.utc(*START).tt
jd = jd0 + np.arange(0, DAYS * 1440, STEP_MIN) / 1440.0
t = eph.tt(jd)
moon = eph.longitude("moon", t)
sun = eph.longitude("sun", t)
planets = {b: eph.longitude(b, t) for b in MODERN}

tl = Timeline(eph, jd0, jd[-1], MODERN)
defs = {
    "modern": void_of_course(eph, jd0 - 1, jd[-1] + 1, MODERN),
    "traditional": void_of_course(eph, jd0 - 1, jd[-1] + 1, TRADITIONAL),
    "lilly": lilly_void(eph, jd0 - 1, jd[-1] + 1),
    "lilly_unbounded": lilly_void(eph, jd0 - 1, jd[-1] + 1, bound="none"),
}

frames = []
for i, j in enumerate(jd):
    st = tl.state(j)
    c = st.dominant
    if c is None:
        dom, tone, bri = None, 0, 0.0
    else:
        across = st.crosses_sign(c)
        d = c.depth(j)
        lo, hi = (0.15, 0.25) if across else (0.60, 1.00)
        dom = [MODERN.index(c.body), int(c.angle), round(d, 3), 0 if across else 1]
        tone, bri = (1 if c.traditional else 2), round(lo + (hi - lo) * d, 3)
    mask = sum(1 << k for k, ps in enumerate(defs.values())
               if any(p.start_jd <= j < p.end_jd for p in ps))
    frames.append({
        "m": round(float(moon[i]), 2),
        "e": round(float((moon[i] - sun[i]) % 360), 1),
        "s": SIGNS.index(st.sign),
        "p": [round(float(planets[b][i]), 2) for b in MODERN],
        "d": dom, "t": tone, "b": bri, "v": mask,
    })

data = {
    "start": eph.tt(jd0).utc_iso(),
    "stepMin": STEP_MIN,
    "bodies": list(MODERN),
    "traditional": [b in TRADITIONAL for b in MODERN],
    "thr": [round(contact_distance(b, LILLY_ORBS), 2) for b in MODERN],
    "orbs": {b: LILLY_ORBS[b] for b in ("moon", *MODERN)},
    "defs": list(defs),
    "frames": frames,
}
blob = json.dumps(data, separators=(",", ":"))
tpl = (HERE / "astrolabe.template.html").read_text()
page = tpl.replace("/*__DATA__*/null", blob)
(HERE / "astrolabe.html").write_text(page)  # fragment: the artifact host adds the document skeleton

# GitHub Pages needs a whole document
docs = HERE.parents[1] / "docs"
docs.mkdir(exist_ok=True)
(docs / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="A lunar month of Lilly\'s orbs on a zodiac wheel, and the bulb color '
    'Sublunary would produce, frame by frame.">\n'
    '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}img{max-width:100%}'
    '[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);'
    'padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
    + page.replace("</style>", "</style>\n</head>\n<body>", 1)
    + "\n</body>\n</html>\n")
(docs / ".nojekyll").write_text("")
print(f"{len(frames)} frames, {len(blob)/1024:.0f} KB")
