"""Write a weekly update for any local repo, and show which sentences hold up.

    python scripts/report.py ~/code/some-client --limit 40
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.compose import ModelUnavailable, write_update
from app.gitlog import era, read_commits
from app.receipts import find_true_receipt
from app.trace import judge

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo")
    parser.add_argument("--limit", type=int, default=40, help="commits to read (default 40)")
    parser.add_argument("--variant", choices=["base", "primed"], default="primed")
    parser.add_argument("--all", action="store_true", help="also print the receipts that hold")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(f"  not a git repository: {repo}", file=sys.stderr)
        return 2

    commits = read_commits(str(repo), limit=args.limit)
    if not commits:
        print("  no commits in range", file=sys.stderr)
        return 2

    first, last = era(commits)
    print(f"\n  {repo.name}: {len(commits)} commits, {first} -> {last}\n")

    try:
        bullets = write_update(commits, variant=args.variant)
    except ModelUnavailable as exc:
        print(f"  model unavailable: {exc}", file=sys.stderr)
        print("  start it with: ollama serve", file=sys.stderr)
        return 1

    lookup = {c.short: c for c in commits}
    flagged = 0

    for bullet in bullets:
        cites = bullet.get("cites") or []
        verdicts = [(sha, judge(bullet["text"], sha, commits)) for sha in cites]
        winners = [(sha, v) for sha, v in verdicts if v.clean]
        ok = bool(winners)
        flagged += not ok

        print(f"  {'ok  ' if ok else 'FAIL'} {bullet['text']}")

        if ok and not args.all:
            continue

        if not cites:
            print("       no receipt offered")
            continue

        for sha, verdict in verdicts:
            commit = verdict.commit
            label = commit.message if commit else "not in this window"
            mark = "supports" if verdict.clean else "does not support"
            print(f"       [{sha}] {mark} — {label}")
            for finding in verdict.findings:
                print(f"           {finding.rule}: {finding.detail}")

        if not ok:
            needed = find_true_receipt(bullet["text"], commits)
            if needed:
                print(f"       needed [{needed}] {lookup[needed].message}")
            else:
                print(
                    "       no commit message explains this one — open the diff before "
                    "sending, or cut the sentence"
                )

    total = len(bullets)
    print(f"\n  {flagged} of {total} receipts do not support their sentence.")
    print(f"  {total - flagged} hold. Read the flagged ones before sending.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
