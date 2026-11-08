"""Build the score page. docs/index.html is public and opens on example charts.

notes/score/score.html (gitignored) is a private build: it also takes first_chart.json and second_chart.json,
both gitignored because they are real people's birth data.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
import json
texts = {k: (json.loads((HERE / "texts" / f"{f}.json").read_text()) if (HERE / "texts" / f"{f}.json").exists() else {})
         for k, f in (("sign", "planet_in_sign"), ("house", "planet_in_house"), ("cond", "conditions"))}
page = (HERE / "score.template.html").read_text().replace("/*__BODIES__*/null", (HERE / "bodies.json").read_text())
page = page.replace("/*__TEXTS__*/null", json.dumps(texts, ensure_ascii=False))


def inject(text, tag, name):
    f = HERE / name
    return text.replace(tag, f.read_text().strip() if f.exists() else "null")


# the Cantata is the front page of sublunary.app
(ROOT / "docs" / "index.html").write_text(page.replace("/*__FIRST__*/null", "null").replace("/*__SECOND__*/null", "null"))
# its earlier addresses, kept so links already shared still arrive, views included
for old_name in ("cantata.html", "score.html"):
    (ROOT / "docs" / old_name).write_text(
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Sublunary: Cantata</title>\n'
        '<meta http-equiv="refresh" content="0; url=./"><link rel="canonical" href="https://sublunary.app/">\n'
        '<script>location.replace("./" + location.hash);</script></head>\n'
        '<body><a href="./">Sublunary: Cantata has moved to the front page.</a></body></html>\n')
private = inject(inject(page, "/*__FIRST__*/null", "first_chart.json"), "/*__SECOND__*/null", "second_chart.json")
(HERE / "score.html").write_text(private)
print(f"public {len(page) / 1024:.0f} KB; private build written")
