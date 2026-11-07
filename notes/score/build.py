"""Build the score page. docs/score.html is public and opens on example charts.

notes/score/score.html (gitignored) is a private build: it also takes first_chart.json and second_chart.json,
both gitignored because they are real people's birth data.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
page = (HERE / "score.template.html").read_text().replace("/*__BODIES__*/null", (HERE / "bodies.json").read_text())


def inject(text, tag, name):
    f = HERE / name
    return text.replace(tag, f.read_text().strip() if f.exists() else "null")


(ROOT / "docs" / "score.html").write_text(page.replace("/*__FIRST__*/null", "null").replace("/*__SECOND__*/null", "null"))
private = inject(inject(page, "/*__FIRST__*/null", "first_chart.json"), "/*__SECOND__*/null", "second_chart.json")
(HERE / "score.html").write_text(private)
print(f"public {len(page) / 1024:.0f} KB; private build written")
