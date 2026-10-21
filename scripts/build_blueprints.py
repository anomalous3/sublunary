"""Generate the Sublunary blueprints from shared pieces.

Power, void and fade behavior live here once, so the blueprints can't drift.
Run: python3 scripts/build_blueprints.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "blueprints" / "automation" / "sublunary"

BODIES = ("sun", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto")
SIGNS = ("aries", "taurus", "gemini", "cancer", "leo", "virgo",
         "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")

# A palette value is [r, g, b], or an int for a white in kelvin (uses the bulb's white LEDs).
HYBRID = {"sun": 2700, "mercury": [190, 205, 255], "venus": [40, 220, 90], "mars": [255, 30, 10],
          "jupiter": [150, 60, 255], "saturn": [60, 40, 210], "uranus": [0, 225, 255],
          "neptune": [20, 90, 255], "pluto": [235, 20, 140]}
GOLDEN_DAWN = {**HYBRID, "sun": [255, 120, 0], "mercury": [255, 225, 0], "venus": [0, 200, 90],
               "mars": [255, 20, 30], "jupiter": [140, 40, 255], "saturn": [70, 30, 180]}
BODY_LABEL = {"sun": "Sun", "mercury": "Mercury (quicksilver)", "venus": "Venus (green)", "mars": "Mars (red)",
              "jupiter": "Jupiter (violet)", "saturn": "Saturn (deep indigo)", "uranus": "Uranus (electric cyan)",
              "neptune": "Neptune (sea blue)", "pluto": "Pluto (magenta)"}

ELEMENT_RGB = {"fire": [255, 60, 10], "earth": [40, 200, 60], "air": [0, 200, 255], "water": [20, 60, 255]}
ELEMENT_OF = {s: e for e, ss in {"fire": ("aries", "leo", "sagittarius"),
                                 "earth": ("taurus", "virgo", "capricorn"),
                                 "air": ("gemini", "libra", "aquarius"),
                                 "water": ("cancer", "scorpio", "pisces")}.items() for s in ss}
ELEMENTS = {s: ELEMENT_RGB[ELEMENT_OF[s]] for s in SIGNS}
# Golden Dawn King scale for the signs: the spectrum walked around the zodiac
GD_SIGNS = {"aries": [255, 20, 20], "taurus": [255, 70, 0], "gemini": [255, 120, 0], "cancer": [255, 170, 0],
            "leo": [240, 230, 0], "virgo": [170, 230, 0], "libra": [0, 200, 80], "scorpio": [0, 170, 170],
            "sagittarius": [20, 90, 255], "capricorn": [60, 30, 190], "aquarius": [140, 40, 255],
            "pisces": [220, 0, 90]}


def fmt(v):
    return f"[{v[0]}, {v[1]}, {v[2]}]" if isinstance(v, list) else str(v)


def mapping(d, indent):
    return "\n".join(f"{indent}{k}: {fmt(v)}" for k, v in d.items())


def rgb_input(key, label, default, indent):
    return (f"{indent}{key}:\n{indent}  name: {label}\n{indent}  default: {fmt(default)}\n"
            f"{indent}  selector:\n{indent}    color_rgb: {{}}")


LIGHTS_INPUT = """    lights:
      name: Lights
      description: Lights that should follow the sky.
      selector:
        entity:
          filter:
            domain: light
          multiple: true"""

POWER_INPUT = """    power:
      name: Power
      description: >
        Only adjusting lights that are on means a light someone turned off stays
        off. Turning it back on hands it to Sublunary again.
      default: only_when_on
      selector:
        select:
          options:
            - label: Only adjust lights that are on (never turns a light on)
              value: only_when_on
            - label: Full control (turns lights on and off)
              value: full_control"""

VOID_INPUTS = """    void_style:
      name: When nothing is applying (void)
      default: dim
      selector:
        select:
          options:
            - label: Dim moonlight
              value: dim
            - label: Off (only with full control)
              value: "off"
    void_appearance:
      name: Void moonlight
      collapsed: true
      input:
        void_kelvin:
          name: White temperature
          default: 4000
          selector:
            color_temp:
              unit: kelvin
              min: 2000
              max: 6500
        void_brightness:
          name: Brightness
          default: 3
          selector:
            number:
              min: 1
              max: 30
              unit_of_measurement: "%\""""

TRANSITION_INPUT = """    transition:
      name: Transition (seconds)
      default: 120
      selector:
        number:
          min: 0
          max: 600
          unit_of_measurement: s"""

CONTACT_INPUT = """    contact_sensor:
      name: Dominant contact sensor
      selector:
        entity:
          filter:
            integration: sublunary
            domain: sensor"""

COMMON_TRIGGERS = """  - trigger: homeassistant
    event: start
  # saving an automation in the UI reloads automations: apply immediately
  - trigger: event
    event_type: automation_reloaded
  # a light turned back on picks up the sky at once
  - trigger: state
    entity_id: !input lights
    from: "off"
    to: "on\""""

COMMON_VARS = """  lights: !input lights
  power: !input power
  base_transition: !input transition"""

VOID_VARS = """  void_style: !input void_style
  void_kelvin: !input void_kelvin
  void_brightness: !input void_brightness"""

NO_VOID_VARS = """  void_style: dim
  void_kelvin: 4000
  void_brightness: 3"""

CONTACT_VARS = """  sensor: !input contact_sensor
  body: "{{ states(sensor) }}"
  applying: "{{ body not in ['none', 'unknown', 'unavailable'] }}"
  # consensus brightness: bright in-sign, faint across the boundary
  bri: >-
    {% set d = state_attr(sensor, 'depth') | float(0) %}
    {% if state_attr(sensor, 'in_sign') %}{{ (60 + 40 * d) | round(0) | int }}
    {% else %}{{ (15 + 10 * d) | round(0) | int }}{% endif %}
  # under a simulated clock, fades shrink with it
  fade: "{{ (base_transition / (state_attr(sensor, 'clock_speed') | float(1))) | round(1) }}\""""

# color is None (void), an int (white in kelvin), or [r, g, b]
ACTIONS = """actions:
  - repeat:
      for_each: "{{ lights }}"
      sequence:
        - if: "{{ power == 'full_control' or is_state(repeat.item, 'on') }}"
          then:
            - choose:
                - conditions: "{{ color is none and void_style == 'off' and power == 'full_control' }}"
                  sequence:
                    - action: light.turn_off
                      target:
                        entity_id: "{{ repeat.item }}"
                      data:
                        transition: "{{ fade }}"
                - conditions: "{{ color is none }}"
                  sequence:
                    - action: light.turn_on
                      target:
                        entity_id: "{{ repeat.item }}"
                      data:
                        color_temp_kelvin: "{{ void_kelvin | int }}"
                        brightness_pct: "{{ void_brightness | int }}"
                        transition: "{{ fade }}"
                - conditions: "{{ color is number }}"
                  sequence:
                    - action: light.turn_on
                      target:
                        entity_id: "{{ repeat.item }}"
                      data:
                        color_temp_kelvin: "{{ color | int }}"
                        brightness_pct: "{{ bri }}"
                        transition: "{{ fade }}"
              default:
                - action: light.turn_on
                  target:
                    entity_id: "{{ repeat.item }}"
                  data:
                    rgb_color: "{{ color }}"
                    brightness_pct: "{{ bri }}"
                    transition: "{{ fade }}"
"""


def blueprint(name, description, inputs, triggers, variables):
    return (f"# Generated by scripts/build_blueprints.py; edit there, not here.\n"
            f"blueprint:\n  name: {name}\n  description: >\n"
            + "\n".join("    " + line for line in description.strip().splitlines())
            + "\n  domain: automation\n  input:\n" + "\n".join(inputs)
            + "\n\nmode: restart\n\ntriggers:\n" + triggers
            + "\n\nvariables:\n" + variables + "\n\n" + ACTIONS)


def consensus():
    inputs = [CONTACT_INPUT, LIGHTS_INPUT, POWER_INPUT, VOID_INPUTS,
              rgb_input("warm_color", "Warm color (traditional planets)", [255, 140, 40], "    "),
              rgb_input("cool_color", "Cool color (outer planets)", [80, 140, 255], "    "),
              TRANSITION_INPUT]
    variables = "\n".join([COMMON_VARS, VOID_VARS, CONTACT_VARS,
                           "  warm: !input warm_color\n  cool: !input cool_color",
                           '  color: "{{ (warm if state_attr(sensor, \'tone\') == \'warm\' else cool) if applying else none }}"'])
    return blueprint(
        "Sublunary consensus light",
        """Hue says which kind of planet the Moon is reaching for (warm: the seven
traditional bodies, cool: Uranus, Neptune, Pluto). Brightness says how many
void-of-course definitions agree she is reaching at all: bright when the
contact perfects in her current sign, faint when only Lilly's orbs reach
across the boundary. With nothing applying, a dim moonlight or off.""",
        inputs,
        "  # no \"to:\" so attribute changes (depth, in_sign) also trigger\n"
        "  - trigger: state\n    entity_id: !input contact_sensor\n" + COMMON_TRIGGERS,
        variables)


def planet_colors():
    custom_inputs = "\n".join(
        [rgb_input(f"{b}_color", BODY_LABEL[b], HYBRID[b] if b != "sun" else [255, 176, 32], "        ")
         for b in BODIES])
    sun_white = """        sun_white:
          name: Sun as warm white
          description: Use the bulb's white LEDs for the Sun instead of the color above.
          default: true
          selector:
            boolean: {}
        sun_kelvin:
          name: Sun white temperature
          default: 2700
          selector:
            color_temp:
              unit: kelvin
              min: 2000
              max: 6500"""
    scheme = """    scheme:
      name: Color scheme
      default: hybrid
      selector:
        select:
          options:
            - label: Hybrid (telescope where it has color, tradition elsewhere; the Sun warm white)
              value: hybrid
            - label: Golden Dawn (outer planets from Hybrid)
              value: golden_dawn
            - label: Custom (the colors below)
              value: custom
    custom_colors:
      name: Custom colors
      description: Used when the scheme is Custom. Prefilled with Hybrid.
      collapsed: true
      input:
""" + sun_white + "\n" + custom_inputs
    inputs = [CONTACT_INPUT, LIGHTS_INPUT, POWER_INPUT, VOID_INPUTS, scheme, TRANSITION_INPUT]
    custom_vars = "\n".join(
        ["  sun_white: !input sun_white", "  sun_kelvin: !input sun_kelvin", "  sun_rgb: !input sun_color"]
        + [f"  {b}_rgb: !input {b}_color" for b in BODIES if b != "sun"]
        + ["  custom:", '    sun: "{{ sun_kelvin if sun_white else sun_rgb }}"']
        + [f'    {b}: "{{{{ {b}_rgb }}}}"' for b in BODIES if b != "sun"])
    variables = "\n".join([
        COMMON_VARS, VOID_VARS, CONTACT_VARS, "  scheme: !input scheme",
        "  palettes:\n    hybrid:\n" + mapping(HYBRID, "      ") + "\n    golden_dawn:\n" + mapping(GOLDEN_DAWN, "      "),
        custom_vars,
        "  palette: \"{{ custom if scheme == 'custom' else palettes[scheme] }}\"",
        '  color: "{{ palette[body] if applying and body in palette else none }}"'])
    return blueprint(
        "Sublunary planet colors",
        """The bulb takes the color of the planet the Moon is reaching for. Brightness
works as in the consensus light: bright when the contact perfects in her
current sign, faint when only Lilly's orbs reach across the boundary. Hybrid
uses what you'd see through a telescope where a planet has a color, tradition
where it's only white or grey, and the bulb's warm white for the Sun. Golden
Dawn uses the King scale for the seven classical planets.""",
        inputs,
        "  # no \"to:\" so attribute changes (depth, in_sign) also trigger\n"
        "  - trigger: state\n    entity_id: !input contact_sensor\n" + COMMON_TRIGGERS,
        variables)


def zodiac_colors(kind):
    """kind: "sign" (the Moon's sign) or "house" (the Moon's natal house, via the natural correspondence)."""
    is_house = kind == "house"
    sensor_input = ("""    house_sensor:
      name: Moon house sensor
      selector:
        entity:
          filter:
            integration: sublunary
            domain: sensor""" if is_house else """    sign_sensor:
      name: Moon sign sensor
      selector:
        entity:
          filter:
            integration: sublunary
            domain: sensor""")
    label = (lambda i, s: f"House {i + 1} (natural {s.capitalize()})") if is_house else (lambda i, s: s.capitalize())
    custom_inputs = "\n".join(rgb_input(f"{s}_color", label(i, s), ELEMENTS[s], "        ") for i, s in enumerate(SIGNS))
    scheme = """    scheme:
      name: Color scheme
      default: elements
      selector:
        select:
          options:
            - label: Elements (fire, earth, air, water)
              value: elements
            - label: Golden Dawn zodiac spectrum
              value: golden_dawn
            - label: Custom (the colors below)
              value: custom
    brightness:
      name: Brightness
      default: 70
      selector:
        number:
          min: 1
          max: 100
          unit_of_measurement: "%"
    custom_colors:
      name: Custom colors
      description: Used when the scheme is Custom. Prefilled with Elements.
      collapsed: true
      input:
""" + custom_inputs
    inputs = [sensor_input, LIGHTS_INPUT, POWER_INPUT, scheme, TRANSITION_INPUT]
    sensor_var = "!input house_sensor" if is_house else "!input sign_sensor"
    # houses arrive as "1".."12"; map them onto their natural signs
    key = ("{% set signs = " + str(list(SIGNS)) + " %}{{ signs[(states(sensor) | int(0)) - 1] if states(sensor) | int(0) > 0 else 'none' }}"
           if is_house else "{{ states(sensor) }}")
    variables = "\n".join([
        COMMON_VARS, NO_VOID_VARS, f"  sensor: {sensor_var}", "  scheme: !input scheme",
        "  bri: !input brightness",
        f'  key: "{key}"',
        "  palettes:\n    elements:\n" + mapping(ELEMENTS, "      ") + "\n    golden_dawn:\n" + mapping(GD_SIGNS, "      "),
        "  custom:\n" + "\n".join(f"    {s}: !input {s}_color" for s in SIGNS),
        "  palette: \"{{ custom if scheme == 'custom' else palettes[scheme] }}\"",
        '  color: "{{ palette[key] if key in palette else none }}"',
        "  fade: \"{{ (base_transition / (state_attr('sensor.sublunary_clock', 'speed') | float(1))) | round(1) }}\""])
    name = "Sublunary house colors" if is_house else "Sublunary sign colors"
    desc = ("""The bulb takes a color for the natal house the Moon is passing through.
Houses use the colors of their natural signs (1st Aries, 2nd Taurus, and so
on). Needs a natal chart set in Sublunary's options.""" if is_house else
            """The bulb takes a color for the sign the Moon is in: by element, or the
Golden Dawn spectrum walked around the zodiac.""")
    trig = (f"  - trigger: state\n    entity_id: !input {'house_sensor' if is_house else 'sign_sensor'}\n"
            + COMMON_TRIGGERS)
    return blueprint(name, desc, inputs, trig, variables)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fname, text in (("consensus_light.yaml", consensus()), ("planet_colors.yaml", planet_colors()),
                        ("sign_colors.yaml", zodiac_colors("sign")), ("house_colors.yaml", zodiac_colors("house"))):
        (OUT / fname).write_text(text)
        print("wrote", fname)
