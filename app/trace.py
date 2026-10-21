"""Check a generated claim against the commit it cites.

Three rules, all deterministic. The point is not to judge writing quality; it is to
catch the specific way a status report goes wrong. The model rarely invents work. It
promotes it: `fix null check` becomes "improved system reliability". Every upgrade is
locally defensible and collectively a lie, which is exactly why nobody catches it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .gitlog import Commit

VERB_RANK = {
    "typo": 1, "format": 1, "black": 1, "lint": 1, "tidy": 1, "whitespace": 1,
    "rename": 1, "bump": 1, "comment": 1, "document": 1, "docs": 1, "pin": 1,
    "move": 1, "style": 1,
    "fix": 2, "guard": 2, "handle": 2, "skip": 2, "check": 2, "correct": 2,
    "patch": 2, "clamp": 2, "validate": 2, "repair": 2, "restore": 2,
    "add": 3, "support": 3, "introduce": 3, "implement": 3, "create": 3,
    "test": 3, "export": 3, "retry": 3, "cover": 3, "wire": 3,
    "refactor": 4, "restructure": 4, "extract": 4, "replace": 4, "migrate": 4,
    "convert": 4, "split": 4, "rewrite": 4, "redesign": 4, "rebuild": 4,
    "overhaul": 5, "rearchitect": 5, "transform": 5, "scale": 5, "optimize": 5,
    "optimise": 5, "accelerate": 5, "deliver": 5, "architecture": 5,
    "build": 4, "built": 4, "improve": 3, "make": 3, "reduce": 3, "speed": 4,
    "run": 1, "ran": 1, "push": 2, "clean": 1,
}

SCOPE_PHRASES = (
    "the system", "the pipeline", "the codebase", "the platform",
    "the architecture", "end to end", "end-to-end", "across the app",
    "the whole project", "the entire", "throughout", "a full", "full-",
)
SCOPE_NOUNS = re.compile(
    r"\b(?:pipeline|platform|codebase|architecture|system|infrastructure|ecosystem)\b"
)

NUMERIC_CLAIM = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|percent\b|lines?\b|files?\b|tests?\b|retries\b|attempts\b|seconds?\b|ms\b)",
    re.I,
)
VERSION_CLAIM = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")
IDENTIFIER = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b|\b[\w./-]+\.(?:py|md|txt|json|csv|ya?ml)\b")
WORD = re.compile(r"[a-z]+")


@dataclass
class Finding:
    rule: str
    detail: str


@dataclass
class Judgement:
    text: str
    commit: Commit | None
    findings: list[Finding] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.findings


def _commit_text(commit: Commit) -> str:
    files = " ".join(f.path for f in commit.files)
    return f"{commit.message} {files} {commit.diff}".lower()


def _verb_rank(token: str) -> int | None:
    candidates = [token]
    if token.endswith("ed"):
        candidates += [token[:-2], token[:-2] + "e"]
    if token.endswith("ing"):
        candidates += [token[:-3], token[:-3] + "e"]
    if token.endswith("es"):
        candidates.append(token[:-2])
    if token.endswith("s"):
        candidates.append(token[:-1])
    for candidate in candidates:
        if candidate in VERB_RANK:
            return VERB_RANK[candidate]
    return None


def _claim_rank(text: str) -> tuple[int, str | None]:
    """The claim's strength is its leading verb, not its most impressive word."""
    clear = IDENTIFIER.sub(" ", text.lower())
    for token in WORD.findall(clear):
        rank = _verb_rank(token)
        if rank:
            return rank, token
    return 0, None


def _main_clause(text: str) -> str:
    """The claim is the first clause; the rest is usually elaboration."""
    return re.split(r"[,;:]", text, maxsplit=1)[0]


def _message_rank(commit: Commit) -> int:
    """Commit messages lead with the verb; the rest may be nouns that shadow verbs.

    "Document the retry behaviour" is a docs commit, but "retry" is also a strong verb,
    so taking the maximum over the message scores it like work. Take the first instead.
    """
    clear = IDENTIFIER.sub(" ", commit.message.lower())
    for token in WORD.findall(clear):
        rank = _verb_rank(token)
        if rank:
            return rank
    return 2


def _diff_sides(commit: Commit) -> tuple[str, str]:
    added, removed = [], []
    for line in commit.diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return "\n".join(added).lower(), "\n".join(removed).lower()


def _grounding(text: str, commit: Commit) -> list[Finding]:
    source = _commit_text(commit)
    added, removed = _diff_sides(commit)
    message = commit.message.lower()
    findings = []

    for match in NUMERIC_CLAIM.findall(text):
        number = re.match(r"\d+(?:\.\d+)?", match).group()
        if number in added or number in message:
            continue
        if number in removed:
            findings.append(
                Finding(
                    "grounding",
                    f"claim states {match!r}, but the commit deletes that value "
                    f"rather than introducing it",
                )
            )
        elif number not in source:
            findings.append(
                Finding("grounding", f"claim states {match!r}, which the commit never mentions")
            )

    for match in VERSION_CLAIM.findall(text):
        version = match.lower().lstrip("v")
        if version in added or version in message:
            continue
        if version in removed:
            findings.append(
                Finding(
                    "grounding",
                    f"claim states version {match!r}, but the commit removes that "
                    f"version rather than introducing it",
                )
            )
        elif version not in source:
            findings.append(
                Finding("grounding", f"claim states version {match!r}, which the commit never mentions")
            )

    for identifier in IDENTIFIER.findall(text):
        if identifier.lower() not in source:
            findings.append(
                Finding("grounding", f"claim names {identifier!r}, which the commit never touches")
            )

    return findings


def _verb_inflation(text: str, commit: Commit) -> list[Finding]:
    claim_rank, word = _claim_rank(_main_clause(text))
    commit_rank = _message_rank(commit)
    if word and claim_rank - commit_rank >= 2:
        return [
            Finding(
                "inflation",
                f"claim says {word!r} (strength {claim_rank}) for a commit that says "
                f"{commit.message!r} (strength {commit_rank})",
            )
        ]
    return []


def _scope_inflation(text: str, commit: Commit) -> list[Finding]:
    lowered = text.lower()
    broad = [phrase for phrase in SCOPE_PHRASES if phrase in lowered]
    broad += SCOPE_NOUNS.findall(lowered)
    if not broad:
        return []

    narrow_commit = commit.touched <= 1
    small_commit = _message_rank(commit) <= 2
    if narrow_commit or small_commit:
        return [
            Finding(
                "scope",
                f"claim reaches for {broad[0]!r} on a commit that says "
                f"{commit.message!r} and touched {commit.touched} file(s), {commit.churn} lines",
            )
        ]
    return []


def judge(text: str, cited: str | None, commits: list[Commit]) -> Judgement:
    if not cited:
        return Judgement(text=text, commit=None, findings=[Finding("citation", "no commit cited")])

    lookup = {c.sha: c for c in commits} | {c.short: c for c in commits}
    commit = lookup.get(cited.strip().strip("`"))
    if commit is None:
        return Judgement(
            text=text,
            commit=None,
            findings=[Finding("citation", f"cites {cited!r}, which is not in the window")],
        )

    findings = _grounding(text, commit) + _verb_inflation(text, commit) + _scope_inflation(text, commit)
    return Judgement(text=text, commit=commit, findings=findings)
