"""Render 'The Moon Through Lilly's Orbs, on the Sphere' from year.npz."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle

from sublunary.moieties import LILLY_ORBS, contact_distance

HERE = Path(__file__).resolve().parent
D = np.load(HERE / "year.npz")
jd, m_lat, m_lon, sphere, flat = D["jd"], D["m_lat"], D["m_lon"], D["sphere"], D["flat"]
p_lat, p_lon, s_lon = D["p_lat"], D["p_lon"], D["s_lon"]
BODIES = [str(b) for b in D["bodies"]]

INK, INK2, LINE, FG, MUTED, SILVER = "#0d0f17", "#151827", "#262b40", "#dde0ea", "#8b91a8", "#eef1f8"
# Hybrid palette from the planet colors blueprint; the Sun's 2700 K white shown as a warm white
HYBRID = {"sun": (255, 214, 170), "mercury": (190, 205, 255), "venus": (40, 220, 90), "mars": (255, 30, 10),
          "jupiter": (150, 60, 255), "saturn": (60, 40, 210), "uranus": (0, 225, 255), "neptune": (20, 90, 255),
          "pluto": (235, 20, 140)}
COL = np.array([np.array(HYBRID[b]) / 255 for b in BODIES])
GLYPH = {"sun": "☉", "mercury": "☿", "venus": "♀", "mars": "♂", "jupiter": "♃", "saturn": "♄",
         "uranus": "♅", "neptune": "♆", "pluto": "♇"}
ASPECT_GLYPH = {0: "☌", 60: "⚹", 90: "□", 120: "△", 180: "☍"}
SIGN_GLYPH = "♈♉♊♋♌♍♎♏♐♑♒♓"
TITLE, LABEL, SYM = "Hoefler Text", "Avenir Next", "DejaVu Sans"
wrap = lambda x: (x + 180) % 360 - 180

dom = sphere.argmax(0)
depth = sphere.max(0)
ghost = (flat.max(0) > 0) & (depth == 0)


def segment_style(idx):
    """Per-sample color and width for the Moon's thread."""
    colors = np.zeros((len(idx), 4))
    widths = np.zeros(len(idx))
    for n, i in enumerate(idx):
        if depth[i] > 0:
            colors[n, :3] = COL[dom[i]]
            colors[n, 3] = 0.35 + 0.65 * depth[i]
            widths[n] = 0.8 + 3.2 * depth[i]
        elif ghost[i]:
            colors[n] = (0.55, 0.57, 0.66, 0.22)   # void on the sphere; marked separately
            widths[n] = 0.6
        else:
            colors[n] = (0.55, 0.57, 0.66, 0.22)
            widths[n] = 0.6
    return colors, widths


fig = plt.figure(figsize=(16, 23), facecolor=INK)

# ---------------------------------------------------------------- title
fig.text(0.06, 0.972, "The Moon Through Lilly's Orbs, on the Sphere", fontfamily=TITLE, fontsize=34, color=FG)
fig.text(0.06, 0.955, "Each planet radiates an orb: half its own plus half the Moon's. Flattened onto the ecliptic, the Moon "
         "meets each orb at a straight edge. On the sky she rides up to five degrees above or below it,",
         fontfamily=LABEL, fontsize=11.5, color=MUTED)
fig.text(0.06, 0.946, "so she meets the orb's curved edge instead, a little later. 2026, from JPL DE440s. "
         "Colors are Sublunary's Hybrid planet palette.", fontfamily=LABEL, fontsize=11.5, color=MUTED)

# ---------------------------------------------------------------- panel A: three late touches, true scale
ASPECT_NAME = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}
episodes = []
for k, bname in enumerate(BODIES):
    f = flat[k] > 0
    edges = np.flatnonzero(np.diff(np.concatenate([[0], f.astype(int), [0]])))
    for st, en in zip(edges[::2], edges[1::2]):
        sp = np.flatnonzero(sphere[k, st:en] > 0)
        if sp.size:
            episodes.append((int(sp[0]), k, st, en))
episodes.sort(reverse=True)
chosen, seen = [], set()
for delay, k, st, en in episodes:
    if k not in seen:
        chosen.append((delay, k, st, en)); seen.add(k)
    if len(chosen) == 3:
        break
chosen.sort(key=lambda c: c[2])

fig.text(0.06, 0.925, "Three late touches, at true scale", fontfamily=TITLE, fontsize=20, color=FG)
for n, (delay, k, st, en) in enumerate(chosen):
    ax = fig.add_axes([0.06 + n * 0.305, 0.712, 0.27, 0.185], facecolor=INK)
    bname, col, rho = BODIES[k], COL[k], contact_distance(BODIES[k], LILLY_ORBS)
    mid = (st + en) // 2
    asp = next(a for a in (0, 60, 90, 120, 180, 240, 270, 300)
               if -rho < wrap(m_lon[mid] - (p_lon[k, mid] + a)) <= 0)
    pt_lat = p_lat[k, mid] * np.cos(np.radians(asp))
    win = np.arange(max(0, st - 60), min(len(jd), en + 40))
    dx = wrap(m_lon[win] - (p_lon[k, win] + asp))          # longitude relative to the aspect point
    dy = m_lat[win]
    half = rho + 2.5
    lim = rho + 1.5
    ax.set_xlim(-lim, lim); ax.set_ylim(pt_lat - lim, pt_lat + lim); ax.set_aspect("equal", adjustable="box")
    ax.axhline(0, color=LINE, lw=1, zorder=0)
    # flat model: a band of longitude, straight-edged, on the applying side
    ax.axvspan(-rho, 0, color=(*col, 0.07), lw=0, zorder=0)
    ax.axvline(-rho, color=(*col, 0.55), lw=1, ls=(0, (3, 3)), zorder=1)
    # sphere: a disk around the aspect point
    ax.add_patch(Circle((0, pt_lat), rho, facecolor=(*col, 0.10), edgecolor=(*col, 0.85), lw=1.3, zorder=1))
    ax.plot(0, pt_lat, "o", ms=6, color=col, zorder=4)
    # the Moon's path: void grey, late sliver silver, contact in color
    seg = np.stack([np.column_stack([dx[:-1], dy[:-1]]), np.column_stack([dx[1:], dy[1:]])], axis=1)
    cols, wid = [], []
    for i in win[:-1]:
        if sphere[k, i] > 0:
            cols.append((*col, 0.4 + 0.6 * sphere[k, i])); wid.append(1 + 3 * sphere[k, i])
        elif flat[k, i] > 0:
            cols.append((0.93, 0.95, 0.97, 0.95)); wid.append(2.2)
        else:
            cols.append((0.55, 0.57, 0.66, 0.35)); wid.append(0.9)
    keep = np.abs(np.diff(dx)) < 10
    ax.add_collection(LineCollection(seg[keep], colors=np.array(cols)[keep], linewidths=np.array(wid)[keep], capstyle="round", zorder=3))
    if n == 0:  # a small legend, once
        lab = dict(fontfamily=LABEL, fontsize=9, color=MUTED)
        ax.text(-rho + 0.3, pt_lat - lim + 0.6, "flat edge", **lab)
        ax.text(rho * 0.72, pt_lat - rho * 0.78, "orb on\nthe sphere", ha="left", **lab)
        ax.text(lim - 0.3, 0.35, "ecliptic", ha="right", **lab)
        ax.text(0.5, pt_lat - 0.9, "aspect point", **lab)
    peak = sphere[k, st:en].max()
    date = (np.datetime64("2026-01-01") + np.timedelta64(int((jd[mid] - jd[0]) * 1440), "m")).astype("datetime64[D]")
    month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(str(date)[5:7]) - 1]
    ax.set_title(f"{bname.capitalize()} {ASPECT_NAME[min(asp, 360 - asp)]}, {int(str(date)[8:])} {month}",
                 fontfamily=TITLE, fontsize=15, color=FG, loc="left", pad=6)
    h, m = divmod(delay * 10, 60)
    ax.text(0.0, -0.02, f"touches {h} h {m:02d} m later; peaks at {peak:.2f}, not 1.00",
            transform=ax.transAxes, fontfamily=LABEL, fontsize=10, color=MUTED, va="top")
    ax.set_xticks([]); ax.set_yticks([])
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
fig.text(0.06, 0.684, "The dashed line is where the flat model starts counting contact; the circle is the orb on the sphere. "
         "The Moon passes above or below its aspect point, so she meets the curved edge later, and the white stretch "
         "between them is time the flat model calls contact and the sphere calls void.",
         fontfamily=LABEL, fontsize=10.5, color=MUTED, wrap=True)

# ---------------------------------------------------------------- panel B: the year as a tapestry
axB = fig.add_axes([0.10, 0.075, 0.80, 0.555], facecolor=INK)
starts = np.concatenate([[0], np.nonzero(np.diff(m_lon) < -300)[0] + 1, [len(jd)]])
rows = [(a, b) for a, b in zip(starts[:-1], starts[1:]) if b - a > 1000]
ROW_H, AMP = 1.0, 0.075                                        # one row per lap; latitude drawn at AMP per degree
axB.set_xlim(-2, 362); axB.set_ylim(len(rows) * ROW_H + 0.4, -0.9)
for s in range(13):
    axB.axvline(s * 30, color=LINE, lw=0.8, zorder=0)
    if s < 12:
        axB.text(s * 30 + 15, -0.55, SIGN_GLYPH[s] + "︎", fontfamily=SYM, fontsize=15, color=MUTED, ha="center", va="center")
elong = (m_lon - s_lon) % 360
for r, (a, b) in enumerate(rows):
    base = r * ROW_H + 0.5
    axB.plot([0, 360], [base, base], color=LINE, lw=0.6, zorder=0)
    idx = np.arange(a, b)
    x = m_lon[idx]
    y = base - m_lat[idx] * AMP                                 # north is up
    colors, widths = segment_style(idx)
    segs = np.stack([np.column_stack([x[:-1], y[:-1]]), np.column_stack([x[1:], y[1:]])], axis=1)
    keep = np.abs(np.diff(x)) < 10
    axB.add_collection(LineCollection(segs[keep], colors=colors[:-1][keep], linewidths=widths[:-1][keep] * 0.8,
                                      capstyle="round", zorder=2))
    # late touches: silver ticks just above the thread
    g = ghost[idx]
    starts_g = np.flatnonzero(np.diff(np.concatenate([[0], g.astype(int)])) == 1)
    for c in starts_g:
        axB.plot([x[c], x[c]], [y[c] - 0.13, y[c] - 0.24], color=SILVER, lw=1.1, alpha=0.9, zorder=3)
    # new and full moons on the thread; near the ecliptic they are eclipses
    for target, face in ((0, INK), (180, SILVER)):
        g = wrap(elong[idx] - target)
        for c in np.nonzero((g[:-1] < 0) & (g[1:] >= 0))[0]:
            i = idx[c]
            eclipse = abs(m_lat[i]) < 1.4
            axB.plot(m_lon[i], base - m_lat[i] * AMP, "o", ms=9 if eclipse else 6, mfc=face, mec=SILVER,
                     mew=1.6 if eclipse else 1.0, zorder=4)
            if eclipse:
                axB.text(m_lon[i] + 2.2, base - m_lat[i] * AMP - 0.18, "eclipse", fontfamily=LABEL, fontsize=8.5,
                         color=SILVER, va="center", zorder=4)
    date = (np.datetime64("2026-01-01") + np.timedelta64(int((jd[a] - jd[0]) * 1440), "m")).astype("datetime64[D]")
    axB.text(-4, base, str(date)[5:].replace("-", " / "), fontfamily="Menlo", fontsize=9, color=MUTED, ha="right", va="center")
    axB.text(364, base, f"{ghost[idx].mean():.1%}", fontfamily="Menlo", fontsize=9,
             color=SILVER if ghost[idx].mean() > 0.02 else MUTED, ha="left", va="center")
axB.text(-4, -0.55, "lap began", fontfamily=LABEL, fontsize=8.5, color=MUTED, ha="right", va="center")
axB.text(364, -0.55, "time lost", fontfamily=LABEL, fontsize=8.5, color=MUTED, ha="left", va="center")
axB.set_xticks([]); axB.set_yticks([])
for s in axB.spines.values():
    s.set_visible(False)
fig.text(0.06, 0.648, "2026, one lap of the zodiac per row", fontfamily=TITLE, fontsize=20, color=FG)
fig.text(0.06, 0.637, "The thread is the Moon's latitude, north up, colored by the planet she reaches for on the sphere. "
         "Silver ticks mark late touches; dark and pale discs are new and full moons.", fontfamily=LABEL, fontsize=10.5, color=MUTED)

# ---------------------------------------------------------------- the finding
lat_abs = np.abs(m_lat)
bands = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5.3)]
rates = [ghost[(lat_abs >= lo) & (lat_abs < hi)].mean() for lo, hi in bands]
season = D["node_gap"] < 18
fig.text(0.06, 0.053, "What the year says", fontfamily=TITLE, fontsize=17, color=FG)
finding = [
    "No contact is lost: every one the flat model sees, the sphere sees too. They begin later and peak lower,",
    f"which moves {ghost.mean():.1%} of the year from contact to void, following the Moon's own latitude: "
    + ", ".join(f"{r:.1%}" for r in rates) + " of the time at 0–1 through 4–5 degrees off the ecliptic.",
    f"Eclipse seasons don't matter ({ghost[season].mean():.1%} inside, {ghost[~season].mean():.1%} outside): the Moon "
    "crosses her nodes twice a month whatever the Sun is doing,",
    "so the rhythm is the draconic month, the waves drifting across the rows.",
]
for n, line in enumerate(finding):
    fig.text(0.06, 0.038 - n * 0.0105, line, fontfamily=LABEL, fontsize=10.5, color=MUTED)
fig.text(0.94, 0.004, "Sublunary · github.com/anomalous3/sublunary", fontfamily=LABEL, fontsize=9, color=LINE, ha="right")

out = HERE / "lilly-on-the-sphere.png"
fig.savefig(out, dpi=110, facecolor=INK)
print("wrote", out)
