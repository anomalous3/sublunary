"""Compact city list for birth-place lookup, from GeoNames (CC BY 4.0) via geonamescache.

One line per city, most populous first:  name \t country \t admin1 \t lat \t lon \t timezone
Written gzipped into the integration and plain beside the web pages.
Run: python3 scripts/build_cities.py
"""

import gzip
from pathlib import Path

import geonamescache

ROOT = Path(__file__).resolve().parents[1]
MIN_POPULATION = 5000


def main():
    gc = geonamescache.GeonamesCache(min_city_population=MIN_POPULATION)
    cities = sorted(gc.get_cities().values(), key=lambda c: -int(c.get("population") or 0))
    lines = []
    for c in cities:
        if not c.get("timezone"):
            continue
        name = c["name"].replace("\t", " ")
        lines.append(f"{name}\t{c['countrycode']}\t{c.get('admin1code', '')}\t"
                     f"{c['latitude']:.3f}\t{c['longitude']:.3f}\t{c['timezone']}")
    text = "# GeoNames (geonames.org), CC BY 4.0. Cities of 5000+, most populous first.\n" + "\n".join(lines) + "\n"
    gz = ROOT / "custom_components" / "sublunary" / "cities.txt.gz"
    gz.write_bytes(gzip.compress(text.encode(), mtime=0))
    for d in (ROOT / "docs", ROOT / "notes" / "astrolabe"):
        (d / "cities.txt").write_text(text)
    print(f"{len(lines)} cities; {len(text)/1024:.0f} KB plain, {gz.stat().st_size/1024:.0f} KB gzipped")


if __name__ == "__main__":
    main()
