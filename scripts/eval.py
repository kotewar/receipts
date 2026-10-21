"""Generate updates, check every claim against its receipt, and count the damage."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.compose import write_update
from app.gitlog import era, read_commits
from app.trace import judge

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "fixtures" / "demo-client"
OUT = ROOT / "data"


def check(text: str, cites: list[str], commits) -> dict:
    """A bullet survives if any receipt it offers supports it."""
    if not cites:
        verdict = judge(text, "", commits)
        return {
            "clean": verdict.clean,
            "supported_by": None,
            "mixed": False,
            "commit_message": None,
            "findings": [{"rule": f.rule, "detail": f.detail} for f in verdict.findings],
        }

    verdicts = [(sha, judge(text, sha, commits)) for sha in cites]
    winners = [(sha, v) for sha, v in verdicts if v.clean]
    supported_by = winners[0][0] if winners else None
    fallback = winners[0][1] if winners else verdicts[0][1]
    findings = [{"rule": f.rule, "detail": f.detail} for f in fallback.findings]

    return {
        "clean": bool(winners),
        "supported_by": supported_by,
        "mixed": bool(winners) and len(winners) != len(verdicts),
        "commit_message": fallback.commit.message if fallback.commit else None,
        "findings": findings,
    }


def run(variant: str, runs: int) -> dict:
    commits = read_commits(str(REPO))
    rows = []

    for index in range(runs):
        bullets = write_update(commits, variant=variant)
        for bullet in bullets:
            text = str(bullet.get("text", "")).strip()
            cites = list(bullet.get("cites") or [])
            if not text:
                continue

            verdict = check(text, cites, commits)
            rows.append(
                {
                    "run": index + 1,
                    "text": text,
                    "cites": cites,
                    "cited": cites[0] if cites else "",
                    **verdict,
                }
            )

    return summarise(rows, commits, variant, runs)


def summarise(rows: list[dict], commits, variant: str, runs: int) -> dict:
    flagged = [r for r in rows if not r["clean"]]
    mixed = [r for r in rows if r["mixed"]]
    rules = Counter()
    for row in flagged:
        for rule in {f["rule"] for f in row["findings"]}:
            rules[rule] += 1

    cited = {sha for r in rows for sha in r["cites"]}
    cited_messages = {r["commit_message"] for r in rows if r["commit_message"]}
    never = [c.message for c in commits if c.message not in cited_messages]
    first, last = era(commits)

    return {
        "variant": variant,
        "runs": runs,
        "window": [first, last],
        "commits_in_window": len(commits),
        "bullets": len(rows),
        "clean": len(rows) - len(flagged),
        "flagged": len(flagged),
        "multi_cite": sum(1 for r in rows if len(r["cites"]) > 1),
        "mixed": len(mixed),
        "by_rule": dict(rules),
        "distinct_commits_cited": len(cited),
        "commits_never_mentioned": never,
        "rows": rows,
    }


def show(result: dict) -> None:
    total = result["bullets"]
    flagged = result["flagged"]
    share = (100 * flagged / total) if total else 0
    print(f"\n  {result['variant']}: {result['runs']} run(s), {total} bullets")
    print(f"    clean       {result['clean']:3}  ({100 - share:.0f}%)")
    print(f"    flagged     {flagged:3}  ({share:.0f}%)")
    for rule, count in sorted(result["by_rule"].items()):
        print(f"      {rule:10} {count:3}")
    print(f"    commits cited {result['distinct_commits_cited']}/{result['commits_in_window']}")
    if result["multi_cite"]:
        print(f"    hedged bullets (more than one receipt) {result['multi_cite']}"
              f", of which {result['mixed']} mixed right and wrong")

    flagged_rows = [r for r in result["rows"] if not r["clean"]]
    if flagged_rows:
        print("\n    every flagged bullet, for reading:")
        for row in flagged_rows:
            cites = " ".join(f"[{c}]" for c in row["cites"]) or "[--]"
            print(f"      {cites} {row['text']}")
            for finding in row["findings"]:
                print(f"          {finding['rule']}: {finding['detail']}")

    mixed_rows = [r for r in result["rows"] if r["mixed"]]
    if mixed_rows:
        print("\n    hedged but survivable (a right receipt was offered too):")
        for row in mixed_rows:
            print(f"      {row['supported_by']} saved: {row['text'][:88]}")


def rescore(variant: str) -> dict:
    """Re-judge saved bullets after a gate change, without spending model time."""
    path = OUT / f"eval_{variant}.json"
    data = json.loads(path.read_text())
    commits = read_commits(str(REPO))

    rows = []
    for row in data["rows"]:
        text = row["text"]
        cites = list(row.get("cites") or ([row["cited"]] if row.get("cited") else []))
        verdict = check(text, cites, commits)
        rows.append(
            {"run": row["run"], "text": text, "cites": cites,
             "cited": cites[0] if cites else "", **verdict}
        )

    path.with_suffix(".before.json").write_text(json.dumps(data, indent=2))
    return summarise(rows, commits, variant, data["runs"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["base", "primed", "both"], default="base")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--rescore", action="store_true")
    args = parser.parse_args()

    if args.rescore:
        for variant in (["base", "primed"] if args.variant == "both" else [args.variant]):
            before = json.loads((OUT / f"eval_{variant}.json").read_text())
            result = rescore(variant)
            (OUT / f"eval_{variant}.json").write_text(json.dumps(result, indent=2))
            print(f"\n  {variant}: flagged {before['flagged']}/{before['bullets']} "
                  f"-> {result['flagged']}/{result['bullets']}")
            show(result)
        return

    OUT.mkdir(exist_ok=True)
    variants = ["base", "primed"] if args.variant == "both" else [args.variant]

    for variant in variants:
        result = run(variant, args.runs)
        path = OUT / f"eval_{variant}.json"
        path.write_text(json.dumps(result, indent=2))
        show(result)
        print(f"\n    written to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
