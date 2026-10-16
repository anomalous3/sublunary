# Sublunary

*The realm of change beneath the Moon, rendered in light.*

A Home Assistant integration that turns the Moon's astrological motion into
sensors (sign, phase, applying aspects, void-of-course) so automations can
drive lights from it. It's an art project: the astrology is taken seriously as
a system of definitions, and none of it is claimed as a mechanism.

Void of course is famously contested, so Sublunary computes several
definitions side by side, and the disagreement between them is itself
something you can display.

## Install (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/anomalous3/sublunary`, type **Integration**.
2. Install **Sublunary**, restart Home Assistant.
3. Settings → Devices & services → **Add integration** → Sublunary.

On first setup it downloads NASA JPL's `de440s.bsp` ephemeris (~32 MB, covers
1849–2150) into `config/sublunary/`, so the first start needs internet.

## Entities

| Entity | State | Notable attributes |
|---|---|---|
| `sensor.sublunary_moon_sign` | sign | `next_ingress` |
| `sensor.sublunary_moon_phase` | one of 8 phases | `illumination`, `elongation`, `next_phase`, `next_phase_at` |
| `sensor.sublunary_dominant_contact` | body the Moon is applying to, or `none` | `aspect`, `depth` (0→1 toward perfection), `in_sign`, `tone` (warm/cool), `perfects`, `contacts` |
| `binary_sensor.sublunary_void_of_course_<definition>` | on while void | `start`, `end`, `last_aspect`, `next_start`, `next_end` |
| `sensor.sublunary_clock` | the time Sublunary thinks it is | `simulated`, `speed`, `paused` |

## Void-of-course definitions

- **modern**: from the Moon's last Ptolemaic aspect (to any of Sun through Pluto) until she enters the next sign.
- **traditional**: the same, using only the seven traditional bodies.
- **lilly**: William Lilly's moieties (*Christian Astrology*, 1647). Each body
  has an orb; contact begins when the Moon is within the sum of the half-orbs.
  She's not void if she comes within orbs of an aspect before leaving the sign,
  even if it perfects in the next one.
- **lilly_unbounded**: void whenever no applying contact exists at all, regardless of sign.

The dominant contact uses Lilly's orbs for all bodies (outer planets get a
placeholder 5°, since Lilly never saw them). In-sign contacts outrank
boundary-crossing ones, and depth breaks ties.

## Blueprint: consensus light

`blueprints/automation/sublunary/consensus_light.yaml`. Hue shows which kind of
planet the Moon is reaching for (warm for traditional, cool for outer).
Brightness shows how many definitions agree she's reaching at all: bright
in-sign, faint when only Lilly's orbs reach across the sign boundary, off when
nothing is applying. Import it by URL from the Blueprints page.

## Simulated clock

```yaml
action: sublunary.set_clock
data:
  start: "2026-10-16 01:00:00"   # optional
  speed: 1440                    # a day per real minute
```

`sublunary.reset_clock` returns to real time. Fades in the blueprint shrink
with the clock speed. The clock pauses at the edge of the ephemeris range.

## Accuracy

Positions come from [Skyfield](https://rhodesmill.org/skyfield/) with JPL
DE440s (apparent geocentric, true ecliptic of date). Moon events agree with
the Swiss Ephemeris to about 1 s median (`tests/validate_swe.py`). Void
periods match the moontracks.com table for Oct–Nov 2026 on all 27 periods
(`tests/compare_moontracks.py`; the fixture cites its source).

## Development

```sh
uv venv .venv && uv pip install skyfield numpy pyswisseph   # engine + oracle
python -m tests.validate_swe 2026
uv venv .venv-ha && uv pip install pytest-homeassistant-custom-component skyfield
.venv-ha/bin/python -m pytest                                # real HA core
```

The engine lives in `sublunary/` and is vendored into
`custom_components/sublunary/engine/` by `scripts/vendor_engine.sh`. A test
fails if the two drift apart.

## License

MIT. Ephemeris data: NASA JPL. Orbs: William Lilly, who would have had opinions.
