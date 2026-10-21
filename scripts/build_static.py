"""Bake the demo into one self-contained HTML file for GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

from app.page import PAGE

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "index.html"


def main() -> None:
    data = json.loads((ROOT / "data" / "demo.json").read_text())
    inline = "<script>window.__REPORT__ = " + json.dumps(data) + ";</script>"
    html = PAGE.replace("<!--DATA-->", inline)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"  wrote {OUT.relative_to(ROOT)} ({len(html) / 1024:.1f} KB, data inlined)")


if __name__ == "__main__":
    main()
