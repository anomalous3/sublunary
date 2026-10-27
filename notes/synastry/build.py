"""Wrap the synastry page for GitHub Pages (docs/synastry.html; cities.txt is already beside it)."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
page = (HERE / "synastry.template.html").read_text()
(HERE / "synastry.html").write_text(page)  # fragment for the artifact host
(ROOT / "docs" / "synastry.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Two birth charts as one chord: every aspect between them sounds its interval, '
    'each planet in the voice of its sign, with today\'s sky playing over both.">\n'
    + page.replace("</style>", "</style>\n</head>\n<body>", 1) + "\n</body>\n</html>\n")
print("ok")
