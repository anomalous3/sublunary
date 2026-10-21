"""Offline birth-place search over the bundled GeoNames city list (CC BY 4.0).

Nothing leaves Home Assistant: the list ships with the integration
(scripts/build_cities.py builds it), most populous cities first.
"""

from __future__ import annotations

import gzip
import unicodedata
from functools import lru_cache
from pathlib import Path

FILE = Path(__file__).with_name("cities.txt.gz")


def fold(s: str) -> str:
    """Case- and accent-insensitive form: "São Paulo" -> "sao paulo"."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch)).casefold().strip()


@lru_cache(maxsize=1)
def _cities() -> list[tuple]:
    rows = []
    with gzip.open(FILE, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            name, cc, a1, lat, lon, tz = line.rstrip("\n").split("\t")
            rows.append((fold(name), name, cc, a1, float(lat), float(lon), tz))
    return rows


def search(query: str, limit: int = 12) -> list[dict]:
    """Cities named like the query, exact names first, then prefixes.

    "Springfield, IL" or "Paris, FR" narrow by region code or country code.
    """
    parts = [fold(p) for p in query.split(",") if p.strip()]
    if not parts:
        return []
    name, quals = parts[0], parts[1:]
    exact, prefix = [], []
    for row in _cities():
        if quals and not all(q in (row[2].casefold(), row[3].casefold()) for q in quals):
            continue
        if row[0] == name:
            exact.append(row)
            if len(exact) >= limit:
                break
        elif len(prefix) < limit and row[0].startswith(name):
            prefix.append(row)
    return [{"name": r[1], "country": r[2], "admin1": r[3], "latitude": r[4], "longitude": r[5], "timezone": r[6]}
            for r in (exact + prefix)[:limit]]


def label(p: dict) -> str:
    # GeoNames region codes are readable for some countries (US states) and numeric for others
    region = f"{p['admin1']}, " if p["admin1"] and not p["admin1"].isdigit() else ""
    return f"{p['name']}, {region}{p['country']} ({p['latitude']:.2f}, {p['longitude']:.2f}; {p['timezone']})"
