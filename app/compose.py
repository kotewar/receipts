"""Turn a week of commits into a client update, with a citation on every bullet."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from .gitlog import Commit, render_for_prompt

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("RECEIPTS_MODEL", "gemma3:4b")

BASE_PROMPT = """You write the weekly status update a freelancer sends to a client.

Below are this week's commits from the client's repository. Write 4 to 6 short bullets
describing the week's work, in the order a client would care about. One or two sentences
per bullet, no headings.

Every bullet MUST end with the short sha of the commit it comes from, in square
brackets. A bullet without a citation is invalid and will be rejected.

Return JSON only, with no prose around it:
{"bullets": ["what changed [abc1234]", "what else changed [def5678]"]}

Commits:

__COMMITS__
"""

PRIMED_PROMPT = BASE_PROMPT + """
Be literal. Every factual claim in a bullet must be directly supported by the commit
it cites. If the commit does not mention a number, do not state one. If it changed one
file, do not describe a system-wide change. Do not upgrade a verb: a fix is a fix, a
formatting change is a formatting change.
"""


class ModelUnavailable(RuntimeError):
    pass


def _chat(prompt: str, timeout: int = 240) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ModelUnavailable(str(exc)) from exc

    content = body.get("message", {}).get("content", "")
    if os.environ.get("RECEIPTS_DEBUG"):
        debug = Path("data")
        debug.mkdir(exist_ok=True)
        (debug / "last_content.txt").write_text(content)
        (debug / "last_body.json").write_text(json.dumps(body, indent=2))
    return content


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        return {"bullets": []}
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return {"bullets": []}


SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


def _strip_empty_brackets(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"[\[\(\{]\s*[\]\)\}]", "", text)
    return text


def normalise_bullets(items: list) -> list[dict]:
    bullets = []
    for item in items:
        if isinstance(item, dict):
            text = str(item.get("text", ""))
            explicit = str(item.get("commit") or "")
        else:
            text = str(item)
            explicit = ""

        cites = SHA.findall(text)
        if explicit and explicit not in cites:
            cites.insert(0, explicit)
        for sha in cites:
            text = text.replace(sha, " ")

        text = _strip_empty_brackets(text)
        text = re.sub(r"\s+", " ", text).strip(" .;:,-")
        if text:
            bullets.append({"text": text, "cites": cites})
    return bullets


def write_update(commits: list[Commit], variant: str = "base") -> list[dict]:
    template = PRIMED_PROMPT if variant == "primed" else BASE_PROMPT
    prompt = template.replace("__COMMITS__", render_for_prompt(commits))
    return normalise_bullets(_parse_json(_chat(prompt)).get("bullets", []))
