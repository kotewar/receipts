"""The gate's own test set.

Run: PYTHONPATH=. .venv/bin/python scripts/check_gate.py

Each case is a sentence, the commit it claims, and the rule that must fire
(or None for a sentence that is genuinely supported). Every case came from
reading real model output, not from designing the rules first.
"""

from __future__ import annotations

import sys

from app.gitlog import Commit, FileChange
from app.trace import judge


def commit(message: str, diff: str = "", files: list[str] | str = "app/x.py", sha: str = "aaaaaaa") -> Commit:
    if isinstance(files, str):
        files = [files]
    return Commit(
        sha=sha,
        date="2026-10-20",
        message=message,
        files=[FileChange(path=p, added=1, deleted=0) for p in files],
        diff=diff,
    )


PIN = commit(
    "Pin requests<3",
    diff="-requests==2.31.0\n+requests<3\n",
    files="requirements.txt",
    sha="1111111",
)
BLACK = commit(
    "Run black",
    diff="-def f( x ):\n+def f(x):\n",
    files=["export.py", "invoice.py", "rates.py"],
    sha="2222222",
)
DOCS = commit(
    "Document the retry behaviour",
    diff="+Retries use exponential backoff.\n",
    files="README.md",
    sha="3333333",
)
RETRY = commit(
    "Add retry to fetch_rate",
    diff="+for attempt in range(3):\n",
    files="rates.py",
    sha="4444444",
)
NULLCHECK = commit(
    "Fix null check in parse_invoice",
    diff="-    return row[\"total\"]\n+    if row.get(\"total\") is None: return 0\n",
    files="invoice.py",
    sha="5555555",
)
BUMP = commit(
    "Bump version to 1.2.1",
    diff="-version = \"1.2.0\"\n+version = \"1.2.1\"\n",
    files="pyproject.toml",
    sha="6666666",
)
CLAMP = commit(
    "Clamp retry delay",
    diff="-    return 0.2\n+    return 0.25\n",
    files="rates.py",
    sha="7777777",
)
PIPELINE = commit(
    "Refactor the invoice pipeline",
    diff="+pass\n",
    files=["app/a.py", "app/b.py", "app/c.py", "app/d.py", "app/e.py"],
    sha="8888888",
)
RENAME = commit(
    "Rename qty to quantity",
    diff="-qty = 1\n+quantity = 1\n",
    files="invoice.py",
    sha="abcdef1",
)
TYPO = commit(
    "Fix typo in docs",
    diff="+teh\n-the\n",
    files=["a.md", "b.md", "c.md"],
    sha="9999999",
)
COMMITS = [PIN, BLACK, DOCS, RETRY, NULLCHECK, BUMP, CLAMP, PIPELINE, TYPO, RENAME]

CASES = [
    ("direction: version only in deleted lines", "Refactored the code to pin `requests` to version 2.31.0", PIN, "grounding"),
    ("number the commit never mentions", "Added 12 tests", NULLCHECK, "grounding"),
    ("number present in added lines", "Clamped the delay to 0.25 seconds", CLAMP, None),
    ("file the commit never touches", "Updated `README.md`", PIN, "grounding"),
    ("filename read as a verb", "Ran black to format the code in `export.py`, `invoice.py` and `rates.py`", BLACK, None),
    ("subordinate clause inflating the verb", "Bumped the version to 1.2.1, reflecting the updated retry logic", BUMP, None),
    ("docs commit claimed as implementation", "Implemented retry logic for fetching rates", DOCS, "inflation"),
    ("scope on a one-file commit", "Updated the system to handle retries", RETRY, "scope"),
    ("scope on a wide commit is allowed", "Reworked the platform", PIPELINE, None),
    ("no citation at all", "Did some work", None, "citation"),
    ("citation outside the window", "Did some work", "deadbee", "citation"),
    ("literal claim on a pin commit", "Pinned `requests` below version 3", PIN, None),
    ("add claimed on a rename", "Added a quantity field", RENAME, "inflation"),
    ("docs described as docs", "Documented the retry behaviour", DOCS, None),
    ("test file the commit never adds", "Added a test case in `test_empty.py`", PIN, "grounding"),
    ("refactor claimed on a fix", "Refactored the null check", NULLCHECK, "inflation"),
    ("scope on a small commit touching three files", "Overhauled the system across the app", TYPO, "scope"),
    ("formatter described as itself", "Ran the formatter over the package", BLACK, None),
    ("version present in the message", "Bumped to 1.2.1", BUMP, None),
    ("literal fix on a fix commit", "Fixed the null check in `parse_invoice`", NULLCHECK, None),
]


def main() -> int:
    failures = 0
    for label, text, cited, expected in CASES:
        ref = cited.sha if isinstance(cited, Commit) else cited
        verdict = judge(text, ref, COMMITS)
        rules = {f.rule for f in verdict.findings}
        ok = (not rules) if expected is None else (expected in rules)
        if not ok:
            failures += 1
        mark = "ok  " if ok else "FAIL"
        got = ",".join(sorted(rules)) or "clean"
        want = expected or "clean"
        print(f"{mark} {label:48} want={want:11} got={got}")

    total = len(CASES)
    print(f"\n{total - failures}/{total} cases pass")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
