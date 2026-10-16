"""Generate brand/icon.svg and the PNGs the home-assistant/brands repo wants."""

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RING_C, RING_R = (256, 288), 186
MOON_C, MOON_R = (256, 104), 60          # seated in the ring's opening
SHADOW_C, SHADOW_R = (264, 76), 54       # offset up: lit limb faces down, into the sphere


def _intersections():
    (x0, y0), (x1, y1) = MOON_C, SHADOW_C
    d = math.dist(MOON_C, SHADOW_C)
    a = (MOON_R**2 - SHADOW_R**2 + d * d) / (2 * d)
    h = math.sqrt(MOON_R**2 - a * a)
    mx, my = x0 + a * (x1 - x0) / d, y0 + a * (y1 - y0) / d
    return ((mx + h * (y1 - y0) / d, my - h * (x1 - x0) / d),
            (mx - h * (y1 - y0) / d, my + h * (x1 - x0) / d))


def _arc(center, r, p_from, p_to, via_angle, n=120):
    """Points on a circle from p_from to p_to, going whichever way passes via_angle."""
    ang = lambda p: math.atan2(p[1] - center[1], p[0] - center[0])
    a0, a1 = ang(p_from), ang(p_to)
    ccw = (a1 - a0) % (2 * math.pi)            # sweep length going +angle
    if (via_angle - a0) % (2 * math.pi) > ccw:  # via isn't on the + sweep: go the other way
        ccw -= 2 * math.pi
    return [(center[0] + r * math.cos(a0 + ccw * k / n), center[1] + r * math.sin(a0 + ccw * k / n))
            for k in range(n + 1)]


def crescent_path():
    p, q = _intersections()
    away = math.atan2(MOON_C[1] - SHADOW_C[1], MOON_C[0] - SHADOW_C[0])  # lit limb faces this way
    lit = _arc(MOON_C, MOON_R, p, q, away)
    terminator = _arc(SHADOW_C, SHADOW_R, q, p, away)  # shadow rim inside the moon faces the same way
    pts = lit + terminator[1:-1]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


# tight square around the content (ring stroke at the bottom, crescent tips at the top)
def _crescent_top():
    p, q = _intersections()
    return min(p[1], q[1])


_TOP = _crescent_top() - 8            # tips plus stroke and a hair of margin
_BOTTOM = RING_C[1] + RING_R + 8      # ring plus stroke
_SIDE = max(_BOTTOM - _TOP, 2 * RING_R + 16)
VIEWBOX = f"{256 - _SIDE / 2:.1f} {_TOP:.1f} {_SIDE:.1f} {_SIDE:.1f}"


def ring_dash(gap=150):
    c = 2 * math.pi * RING_R
    top = 0.75 * c  # SVG circles stroke from 3 o'clock, clockwise
    return f"{top - gap / 2:.1f} {gap} {c - top - gap / 2:.1f}"


def svg():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" width="512" height="512">
  <defs>
    <!-- borrowed light: warm at the heart, cooling toward the edge of the sphere -->
    <radialGradient id="glow" cx="{RING_C[0]}" cy="{RING_C[1] + 30}" r="{RING_R + 6}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFD27A" stop-opacity="1"/>
      <stop offset="0.38" stop-color="#FF9A4A" stop-opacity="0.9"/>
      <stop offset="0.8" stop-color="#6F8CFF" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#6F8CFF" stop-opacity="0.1"/>
    </radialGradient>
  </defs>
  <circle cx="{RING_C[0]}" cy="{RING_C[1]}" r="{RING_R - 6}" fill="url(#glow)"/>
  <circle cx="{RING_C[0]}" cy="{RING_C[1]}" r="{RING_R}" fill="none" stroke="#A9B4D0" stroke-width="12"
          stroke-linecap="round" stroke-dasharray="{ring_dash()}"/>
  <path d="{crescent_path()}" fill="#EEF1F8" stroke="#8D9AC0" stroke-width="6" stroke-linejoin="round"/>
</svg>
'''


if __name__ == "__main__":
    import cairosvg
    s = svg()
    (HERE / "icon.svg").write_text(s)
    for size, name in ((512, "icon@2x.png"), (256, "icon.png")):
        cairosvg.svg2png(bytestring=s.encode(), write_to=str(HERE / name), output_width=size, output_height=size)
    if len(sys.argv) > 1:  # preview sheets: light/dark at full size and at 48px
        inner = s.split(">", 1)[1].rsplit("</svg>", 1)[0]
        out = Path(sys.argv[1])
        def sheet(px, pad, scale):
            w = 2 * (px + 2 * pad)
            body = (f'<rect width="{w//2}" height="{px+2*pad}" fill="#FAFAFA"/>'
                    f'<rect x="{w//2}" width="{w//2}" height="{px+2*pad}" fill="#1C1C1E"/>'
                    f'<svg x="{pad}" y="{pad}" width="{px}" height="{px}" viewBox="{VIEWBOX}">{inner}</svg>'
                    f'<svg x="{w//2+pad}" y="{pad}" width="{px}" height="{px}" viewBox="{VIEWBOX}">{inner}</svg>')
            doc = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{px+2*pad}">{body}</svg>'
            return doc, w * scale, (px + 2 * pad) * scale
        for px, pad, scale, name in ((512, 20, 1, "icon_sheet.png"), (48, 26, 4, "icon_small.png")):
            doc, w, h = sheet(px, pad, scale)
            cairosvg.svg2png(bytestring=doc.encode(), write_to=str(out / name), output_width=w, output_height=h)
    print("ok")
