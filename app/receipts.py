"""Find the commit that would actually support a sentence, when one exists.

Passing the three rules is not the same as being supported. A vague sentence can satisfy
a commit of the same strength without sharing a single fact with it, and every commit that
touches `invoice.py` carries the words "null" and "qty" in its diff, so diff overlap says
nothing about which commit did the work. Compare the sentence to the message and the files
the commit names, and take the best match rather than the first.
"""

from __future__ import annotations

import re

from .gitlog import Commit
from .trace import judge

STOP = set(
    "the a an and or to of in for with which that this when from by on as is are was were "
    "has have been it its into within up using including specifically scenario ensuring "
    "allowing able now also potential correct correctly new more less".split()
)

GENERIC = set(
    "add added adds implement implemented create created fix fixed refactor refactored "
    "improve improved update updated bump bumped run ran rename renamed pin pinned "
    "document documented change changed introduce introduced make made generate generated "
    "include including allow allowing ensure ensuring handle handled support supports "
    "use used using remove removed".split()
)


def content_tokens(text: str) -> set[str]:
    """Facts, not the act of changing. 'export' and 'test' are nouns here, so keep them."""
    return {
        token
        for token in re.findall(r"[a-z][a-z0-9_]{2,}", text.lower())
        if token not in STOP and token not in GENERIC
    }


def matched(claim: set[str], hay: set[str]) -> set[str]:
    hits = set()
    for word in claim:
        for other in hay:
            if word == other or (len(other) >= 4 and word.startswith(other)) or (
                len(word) >= 4 and other.startswith(word)
            ):
                hits.add(word)
                break
    return hits


def find_true_receipt(text: str, commits: list[Commit], minimum: int = 2) -> str | None:
    claim = content_tokens(text)
    candidates = []

    for commit in commits:
        if not judge(text, commit.short, commits).clean:
            continue
        hay = content_tokens(f"{commit.message} {' '.join(f.path for f in commit.files)}")
        candidates.append((len(matched(claim, hay)), commit.short, commit.message))

    if not candidates:
        return None
    if len(candidates) == 1:
        # The rules already narrowed it to one commit, and they check the named files.
        return candidates[0][1]

    candidates.sort(key=lambda row: -row[0])
    return candidates[0][1] if candidates[0][0] >= minimum else None
