"""Integration test against real Home Assistant core, clock frozen on 2026-10-16 01:00 UTC.

At that moment the engine says: Moon in Sagittarius, traditionally void since the
Sun sextile (21:55 on the 15th), with Neptune applying across the Capricorn boundary.
"""

import os
from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.yaml import load_yaml
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.components.automation.config import async_validate_config_item
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "data" / "de440s.bsp"
OPTIONS = {"tick_minutes": 5}


def _link_kernel(hass):
    d = hass.config.path("sublunary")
    os.makedirs(d, exist_ok=True)
    link = os.path.join(d, "de440s.bsp")
    if not os.path.lexists(link):
        os.symlink(KERNEL, link)


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_entities_tonight(hass):
    _link_kernel(hass)
    entry = MockConfigEntry(domain="sublunary", data={}, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    sign = hass.states.get("sensor.sublunary_moon_sign")
    dom = hass.states.get("sensor.sublunary_dominant_contact")
    trad = hass.states.get("binary_sensor.sublunary_void_of_course_traditional")
    modern = hass.states.get("binary_sensor.sublunary_void_of_course_modern")
    lilly = hass.states.get("binary_sensor.sublunary_void_of_course_lilly")
    phase = hass.states.get("sensor.sublunary_moon_phase")
    for s in (sign, dom, trad, modern, lilly, phase):
        print(s.entity_id, s.state, dict(s.attributes))

    for s in (sign, dom, trad, modern, lilly, phase):
        assert _no_numpy(dict(s.attributes)), s.entity_id
    assert sign.state == "sagittarius"
    nxt_a = hass.states.get("sensor.sublunary_next_aspect")
    nxt_c = hass.states.get("sensor.sublunary_next_change")
    print(nxt_a.entity_id, nxt_a.state, dict(nxt_a.attributes))
    print(nxt_c.entity_id, nxt_c.state, dict(nxt_c.attributes))
    # next change: the 12:57 ingress, where the Neptune square becomes in-sign
    assert nxt_c.state.startswith("2026-10-16T12:57")
    assert nxt_c.attributes["to"] == "neptune" and nxt_c.attributes["in_sign"] is True
    # Neptune is what's shown now, so next aspect is the one after it: Venus's sextile
    assert nxt_a.state == "venus" and nxt_a.attributes["aspect"] == "sextile"
    assert "void_starts" not in nxt_a.attributes
    assert dom.state == "neptune"
    assert dom.attributes["in_sign"] is False and dom.attributes["tone"] == "cool"
    assert trad.state == "on" and trad.attributes["last_aspect"] == "sextile sun"
    assert modern.state == "on"
    # Lilly counts only traditional bodies: Neptune's reach doesn't save her, but
    # Venus's orb arrives before the ingress, so Lilly's void ends early.
    assert lilly.state == "on"
    assert lilly.attributes["end"] < sign.attributes["next_ingress"]
    # all four definitions exist; the unbounded one starts disabled
    from homeassistant.helpers import entity_registry as er
    reg = er.async_get(hass)
    unb = reg.async_get("binary_sensor.sublunary_void_of_course_lilly_unbounded")
    assert unb is not None and unb.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get("binary_sensor.sublunary_void_of_course_lilly_unbounded") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_config_flow(hass):
    result = await hass.config_entries.flow.async_init("sublunary", context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tick_minutes": 10.0})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"tick_minutes": 10}


@pytest.mark.parametrize("name,sensor_input,sensor", [
    ("consensus_light.yaml", "contact_sensor", "sensor.sublunary_dominant_contact"),
    ("planet_colors.yaml", "contact_sensor", "sensor.sublunary_dominant_contact"),
    ("sign_colors.yaml", "sign_sensor", "sensor.sublunary_moon_sign"),
    ("house_colors.yaml", "house_sensor", "sensor.sublunary_moon_house"),
])
async def test_blueprint_parses(hass, name, sensor_input, sensor):
    bp = Blueprint(load_yaml(ROOT / "blueprints/automation/sublunary" / name),
                   expected_domain="automation", schema=BLUEPRINT_SCHEMA)
    assert {sensor_input, "lights", "power", "transition"} <= set(bp.inputs)
    inputs = BlueprintInputs(bp, {"use_blueprint": {"path": "x.yaml", "input": {
        sensor_input: sensor, "lights": ["light.bedroom"]}}})
    inputs.validate()
    validated = await async_validate_config_item(hass, "test", inputs.async_substitute())
    assert validated is not None and validated.validation_error is None, validated.validation_error


async def test_vendored_engine_in_sync(hass):
    canon = {p.name: p.read_bytes() for p in (ROOT / "sublunary").glob("*.py")}
    vend = {p.name: p.read_bytes() for p in (ROOT / "custom_components/sublunary/engine").glob("*.py")}
    assert canon == vend, "run scripts/vendor_engine.sh"


def _no_numpy(x):
    if isinstance(x, dict):
        return all(_no_numpy(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return all(_no_numpy(v) for v in x)
    return type(x).__module__ != "numpy"


async def _setup(hass):
    _link_kernel(hass)
    entry = MockConfigEntry(domain="sublunary", data={}, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_clock_fast_forward_jump_and_reset(hass, freezer):
    from datetime import timedelta
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    entry = await _setup(hass)
    st = lambda e: hass.states.get(e)

    # a day per minute, continuing from now
    await hass.services.async_call("sublunary", "set_clock", {"speed": 1440}, blocking=True)
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    clock = st("sensor.sublunary_clock")
    assert clock.attributes["simulated"] is True and clock.attributes["speed"] == 1440
    assert clock.state.startswith("2026-10-17T01:00")
    assert st("sensor.sublunary_moon_sign").state == "capricorn"
    dom = st("sensor.sublunary_dominant_contact")
    assert dom.state == "saturn" and dom.attributes["tone"] == "warm" and dom.attributes["in_sign"]
    assert dom.attributes["clock_speed"] == 1440

    # jump back into the whole-sign Leo void of January (forces a timeline rebuild)
    await hass.services.async_call("sublunary", "set_clock",
                                   {"start": "2026-01-04T18:00:00+00:00", "speed": 1}, blocking=True)
    assert st("sensor.sublunary_moon_sign").state == "leo"
    trad = st("binary_sensor.sublunary_void_of_course_traditional")
    assert trad.state == "on" and trad.attributes["last_aspect"] is None
    assert trad.attributes["start"].startswith("2026-01-04T13:4")

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("sublunary", "set_clock", {"start": "2200-01-01T00:00:00+00:00"}, blocking=True)

    await hass.services.async_call("sublunary", "reset_clock", {}, blocking=True)
    assert st("sensor.sublunary_clock").attributes["simulated"] is False
    assert st("sensor.sublunary_moon_sign").state == "sagittarius"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_clock_stops_at_ephemeris_edge(hass, freezer):
    from datetime import timedelta
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    entry = await _setup(hass)
    await hass.services.async_call("sublunary", "set_clock",
                                   {"start": "2148-12-01T00:00:00+00:00", "speed": 100000}, blocking=True)
    for _ in range(4):  # 100000x for 20 min real ~ 4 sim years: well past the edge
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    clock = hass.states.get("sensor.sublunary_clock")
    assert clock.state.startswith("2149-12-01") and clock.attributes["paused"] is True
    assert hass.states.get("sensor.sublunary_moon_sign").state != "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _run_blueprint(hass, name, inputs, light_state="on", name_override=None):
    """Instantiate an automation from one of our blueprints, run it, return light calls."""
    import shutil
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import async_mock_service

    dst = Path(hass.config.path("blueprints/automation/sublunary"))
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "blueprints/automation/sublunary" / name, dst / name)
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    assert await async_setup_component(hass, "automation", {"automation": [{
        "id": "sublunary_test", "alias": "Sublunary planet colors",
        "use_blueprint": {"path": f"sublunary/{name}", "input": {
            **({"sign_sensor": "sensor.sublunary_moon_sign"} if name_override == "sign_sensor"
               else {"contact_sensor": "sensor.sublunary_dominant_contact"}),
            "lights": ["light.bedroom"], **inputs}}}]})
    await hass.async_block_till_done()
    hass.states.async_set("light.bedroom", light_state)
    on.clear(); off.clear()
    await hass.services.async_call("automation", "trigger",
                                   {"entity_id": "automation.sublunary_planet_colors"}, blocking=True)
    await hass.async_block_till_done()
    return on, off


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_planet_colors_hybrid_tonight(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "planet_colors.yaml", {})
    assert not off and len(on) == 1
    data = on[0].data
    assert list(data["rgb_color"]) == [20, 90, 255]          # Neptune, sea blue
    assert 15 <= data["brightness_pct"] <= 25                # across the boundary: faint
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-17 01:00:00+00:00")
async def test_planet_colors_golden_dawn(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "planet_colors.yaml", {"scheme": "golden_dawn"})
    assert not off and len(on) == 1
    data = on[0].data
    assert list(data["rgb_color"]) == [70, 30, 180]          # Saturn, King-scale indigo
    assert 60 <= data["brightness_pct"] <= 100               # in sign: bright
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-15 21:30:00+00:00")
async def test_next_change_into_void(hass):
    entry = await _setup(hass)
    dom = hass.states.get("sensor.sublunary_dominant_contact")
    nxt = hass.states.get("sensor.sublunary_next_change")
    assert dom.state == "sun" and dom.attributes["aspect"] == "sextile"
    assert nxt.state.startswith("2026-10-15T21:55")
    assert nxt.attributes["to"] == "none" and nxt.attributes["aspect"] is None
    # after the Sun sextile the Moon goes void before her next aspect
    na = hass.states.get("sensor.sublunary_next_aspect")
    assert na.state == "void"
    assert na.attributes["void_starts"].startswith("2026-10-15T21:55")
    assert na.attributes["void_ends"].startswith("2026-10-16T12:57")
    assert na.attributes["then"] == "neptune" and na.attributes["aspect"] == "square"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_power_only_when_on_leaves_off_lights_alone(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "planet_colors.yaml", {}, light_state="off")
    assert not on and not off
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-15 21:30:00+00:00")
async def test_sun_is_warm_white(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "planet_colors.yaml", {})
    assert len(on) == 1 and on[0].data["color_temp_kelvin"] == 2700 and "rgb_color" not in on[0].data
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-15 23:00:00+00:00")   # between the Sun sextile and Neptune: void
async def test_void_dim_moonlight_and_full_control_off(hass):
    entry = await _setup(hass)
    assert hass.states.get("sensor.sublunary_dominant_contact").state == "none"
    on, off = await _run_blueprint(hass, "planet_colors.yaml", {})
    assert not off and len(on) == 1
    assert on[0].data["color_temp_kelvin"] == 4000 and on[0].data["brightness_pct"] == 3
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-15 23:00:00+00:00")
async def test_void_off_under_full_control(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "consensus_light.yaml",
                                   {"power": "full_control", "void_style": "off"}, light_state="off")
    assert not on and len(off) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.freeze_time("2026-10-16 01:00:00+00:00")
async def test_sign_colors_elements(hass):
    entry = await _setup(hass)
    on, off = await _run_blueprint(hass, "sign_colors.yaml", {}, name_override="sign_sensor")
    assert len(on) == 1 and list(on[0].data["rgb_color"]) == [255, 60, 10]   # Sagittarius: fire
    assert on[0].data["brightness_pct"] == 70
    assert await hass.config_entries.async_unload(entry.entry_id)
