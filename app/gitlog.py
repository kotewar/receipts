"""Read a week of commits, with enough diff to judge them by."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


@dataclass
class FileChange:
    path: str
    added: int
    deleted: int


@dataclass
class Commit:
    sha: str
    date: str
    message: str
    files: list[FileChange] = field(default_factory=list)
    diff: str = ""

    @property
    def short(self) -> str:
        return self.sha[:7]

    @property
    def churn(self) -> int:
        return sum(f.added + f.deleted for f in self.files)

    @property
    def touched(self) -> int:
        return len(self.files)


def _run(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def read_commits(repo: str, limit: int = 60, diff_chars: int = 700) -> list[Commit]:
    raw = _run(repo, "log", f"--max-count={limit}", "--format=COMMIT %H %as %s", "--numstat", "--no-renames")

    commits: list[Commit] = []
    for line in raw.splitlines():
        if line.startswith("COMMIT "):
            _, sha, date, message = line.split(" ", 3)
            commits.append(Commit(sha=sha, date=date, message=message))
        elif line.strip() and commits:
            parts = line.split("\t")
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                commits[-1].files.append(
                    FileChange(path=parts[2], added=int(parts[0]), deleted=int(parts[1]))
                )

    for commit in commits:
        patch = _run(repo, "show", commit.sha, "--format=", "--patch", "--unified=0")
        commit.diff = patch[:diff_chars]

    return commits


def render_for_prompt(commits: list[Commit]) -> str:
    blocks = []
    for commit in commits:
        files = ", ".join(f"{f.path} +{f.added}-{f.deleted}" for f in commit.files)
        block = [
            f"commit {commit.short}  {commit.date}",
            f"message: {commit.message}",
            f"files: {files or '(none)'}",
        ]
        if commit.diff.strip():
            block.append("diff:")
            block.extend("  " + line for line in commit.diff.splitlines()[:24])
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def era(commits: list[Commit]) -> tuple[str, str]:
    if not commits:
        return "", ""
    dates = sorted(c.date for c in commits)
    return dates[0], dates[-1]
