"""Bake geocentric apparent ecliptic-of-date longitudes for bodies Astronomy Engine lacks, from JPL Horizons.

Writes notes/score/bodies.json: 1900-2100 UT, every 5 days, as base64 little-endian uint16 (360/65536 deg per step).
"""

import base64, json, re, struct, subprocess, urllib.parse
from pathlib import Path

BODIES = {"chiron": "2060;", "ceres": "1;", "pallas": "2;", "juno": "3;", "vesta": "4;"}
START, STOP, STEP = "1900-01-01", "2100-01-01", 5


def fetch(command, start=START, stop=STOP, step=f"{STEP} d"):
    q = dict(format="text", COMMAND=f"'{command}'", OBJ_DATA="NO", MAKE_EPHEM="YES", EPHEM_TYPE="OBSERVER",
             CENTER="'500@399'", START_TIME=f"'{start}'", STOP_TIME=f"'{stop}'", STEP_SIZE=f"'{step}'",
             QUANTITIES="'31'", ANG_FORMAT="DEG", CSV_FORMAT="YES")
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(q)
    # through curl: Python's CA bundle lacks JPL's Entrust root; curl uses the system store and still verifies
    text = subprocess.run(["curl", "-sSf", "--max-time", "180", url], capture_output=True, text=True, check=True).stdout
    body = text.split("$$SOE")[1].split("$$EOE")[0]
    lons = []
    for line in body.strip().splitlines():
        cells = [c.strip() for c in line.split(",")]
        nums = [c for c in cells[1:] if re.fullmatch(r"-?\d+\.\d+", c)]
        lons.append(float(nums[0]))
    return lons


if __name__ == "__main__":
    out = {"start": START, "stepDays": STEP, "scale": 360 / 65536, "bodies": {}}
    for name, cmd in BODIES.items():
        lons = fetch(cmd)
        raw = struct.pack(f"<{len(lons)}H", *[round((x % 360) / 360 * 65536) % 65536 for x in lons])
        out["bodies"][name] = base64.b64encode(raw).decode()
        print(name, len(lons), round(lons[0], 3), round(lons[-1], 3))
    Path(__file__).with_name("bodies.json").write_text(json.dumps(out))
