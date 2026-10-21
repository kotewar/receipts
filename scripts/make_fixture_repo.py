"""Build a small git repo with a week of realistic, deliberately unglamorous work.

The point is not the code. It is the diff: two commits change hundreds of lines and
mean nothing, several are one line, one has a message vague enough to mean anything.
A report generator has to survive that, because that is what a real week looks like.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "demo-client"
AUTHOR = "Sankalp Kotewar"
EMAIL = "sankalp@example.com"


INVOICE_V1 = '''import csv
import json

VERSION = "1.2.0"


def parse_invoice(path):
    rows = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "client": row["client"],
                    "qty": int(row["qty"]),
                    "rate": float(row["rate"]),
                }
            )
    return rows


def total(rows):
    return sum(row["qty"] * row["rate"] for row in rows)


def main(path):
    rows = parse_invoice(path)
    print(json.dumps({"total": total(rows)}))
'''

INVOICE_V2 = INVOICE_V1.replace(
    '''            rows.append(
                {
                    "client": row["client"],
                    "qty": int(row["qty"]),
                    "rate": float(row["rate"]),
                }
            )''',
    '''            qty = row.get("qty")
            if qty in (None, ""):
                continue
            rows.append(
                {
                    "client": row["client"],
                    "qty": int(qty),
                    "rate": float(row["rate"]),
                }
            )''',
)

RATES_V1 = '''import urllib.request


def fetch_rate(base, quote):
    url = f"https://api.example.com/rates?base={base}&quote={quote}"
    with urllib.request.urlopen(url) as response:
        return float(response.read().decode())
'''

RATES_V2 = '''import time
import urllib.request


def fetch_rate(base, quote, attempts=3):
    url = f"https://api.example.com/rates?base={base}&quote={quote}"
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url) as response:
                return float(response.read().decode())
        except OSError as exc:
            last = exc
            time.sleep(0.2 * (attempt + 1))
    raise RuntimeError(f"rate fetch failed after {attempts} attempts") from last
'''

EXPORT = '''import csv


def export_rows(rows, path):
    fields = ["client", "qty", "rate"]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})
'''

TEST_EMPTY = '''from invoice import parse_invoice, total


def test_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("client,qty,rate\\n")
    assert total(parse_invoice(path)) == 0
'''

README_V1 = "# invoice\n\nTurns a CSV of client line items into a total.\n"

README_V2 = (
    "# invoice\n\n"
    "Turns a CSV of client line items into a total.\n\n"
    "Run `python invoice.py lines.csv`.\n"
)

README_V3 = (
    "# invoice\n\n"
    "Turns a CSV of client line items into a total.\n\n"
    "Run `python invoice.py lines.csv`.\n\n"
    "## Rate lookups\n\n"
    "`rates.fetch_rate` retries three times with a short backoff before it raises.\n"
    "The retry exists because the rate provider returns a 502 during its nightly\n"
    "window, which used to surface as a blank total rather than an error.\n"
)

REQUIREMENTS_V1 = "requests==2.31.0\n"
REQUIREMENTS_V2 = "requests<3\n"


def blackened(text):
    return text.replace('"', "'").replace("def ", "def   ").replace("    return", "    return   ")


COMMITS = [
    (
        "Initial commit: invoice totals from a CSV",
        "2026-10-13T10:12:00+0530",
        {
            "invoice.py": INVOICE_V1,
            "README.md": README_V1,
            "requirements.txt": REQUIREMENTS_V1,
        },
    ),
    (
        "Fix typo in README",
        "2026-10-13T16:40:00+0530",
        {"README.md": README_V2},
    ),
    (
        "Fix null check in parse_invoice",
        "2026-10-14T11:05:00+0530",
        {"invoice.py": INVOICE_V2},
    ),
    (
        "Add retry to fetch_rate",
        "2026-10-14T18:22:00+0530",
        {"rates.py": RATES_V2},
    ),
    (
        "Add CSV export",
        "2026-10-15T10:03:00+0530",
        {"export.py": EXPORT},
    ),
    (
        "Rename qty to quantity",
        "2026-10-15T14:47:00+0530",
        {
            "invoice.py": INVOICE_V2.replace("qty", "quantity"),
            "export.py": EXPORT.replace("qty", "quantity"),
        },
    ),
    (
        "Run black",
        "2026-10-15T20:10:00+0530",
        {
            "invoice.py": blackened(INVOICE_V2.replace("qty", "quantity")),
            "export.py": blackened(EXPORT.replace("qty", "quantity")),
            "rates.py": blackened(RATES_V2),
        },
    ),
    (
        "Add test for empty input",
        "2026-10-16T09:31:00+0530",
        {"tests/test_empty.py": TEST_EMPTY},
    ),
    (
        "Pin requests<3",
        "2026-10-16T13:15:00+0530",
        {"requirements.txt": REQUIREMENTS_V2},
    ),
    (
        "Improve error handling",
        "2026-10-16T17:52:00+0530",
        {"rates.py": blackened(RATES_V2.replace("0.2 *", "0.25 *"))},
    ),
    (
        "Bump version to 1.2.1",
        "2026-10-17T10:08:00+0530",
        {},
    ),
    (
        "Document the retry behaviour",
        "2026-10-17T12:26:00+0530",
        {"README.md": README_V3},
    ),
]


def git(*args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def build():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)

    subprocess.run(["git", "init", "-q", "-b", "main", str(ROOT)], check=True)
    git("config", "user.name", AUTHOR)
    git("config", "user.email", EMAIL)

    for message, date, files in COMMITS:
        if message == "Bump version to 1.2.1":
            current = (ROOT / "invoice.py").read_text()
            bumped = re.sub(r"""VERSION = ['"]1\.2\.0['"]""", 'VERSION = "1.2.1"', current)
            (ROOT / "invoice.py").write_text(bumped)
        for name, content in files.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        git("add", "-A")
        git("commit", "-q", "-m", message, date=date)

    print(f"built {ROOT}")
    print(git("log", "--format=%h  %as  %s").rstrip())


if __name__ == "__main__":
    build()
