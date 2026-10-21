"""Turn one saved eval run into the data the demo page serves."""

from __future__ import annotations

import json
from pathlib import Path

from app.gitlog import read_commits
from app.receipts import find_true_receipt
from app.trace import judge

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "fixtures" / "demo-client"
OUT = ROOT / "data" / "demo.json"

VARIANT = "primed"
RUN = 1


def receipt(commit) -> dict:
    return {
        "short": commit.short,
        "message": commit.message,
        "date": commit.date,
        "files": [f.path for f in commit.files],
        "insertions": sum(f.added for f in commit.files),
        "deletions": sum(f.deleted for f in commit.files),
        "diff": commit.diff,
    }



def main() -> None:
    source = json.loads((ROOT / "data" / f"eval_{VARIANT}.json").read_text())
    commits = read_commits(str(REPO))
    lookup = {c.short: c for c in commits}

    rows = [r for r in source["rows"] if r["run"] == RUN]
    bullets = []

    for row in rows:
        needs = None if row["clean"] else find_true_receipt(row["text"], commits)
        bullet = {
            "text": row["text"],
            "cites": row["cites"],
            "clean": row["clean"],
            "findings": row["findings"],
            "receipt": receipt(lookup[row["cites"][0]]),
            "needs": needs,
            "fabricated": (not row["clean"]) and needs is None,
        }
        bullets.append(bullet)

    payload = {
        "client": "demo-client",
        "variant": VARIANT,
        "run": RUN,
        "window": source["window"],
        "commits": [receipt(c) for c in commits],
        "bullets": bullets,
        "stats": {
            "bullets": len(bullets),
            "flagged": sum(1 for b in bullets if not b["clean"]),
            "fabricated": sum(1 for b in bullets if b["fabricated"]),
            "rescued": sum(1 for b in bullets if b["clean"]),
        },
    }

    OUT.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {OUT.relative_to(ROOT)}: {payload['stats']}")


if __name__ == "__main__":
    main()
