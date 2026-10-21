# Receipts

A weekly client update where every sentence carries the commit it came from — and a
deterministic checker that tells you which receipts do not support the sentence above them.

A local 4B model (`gemma3:4b`) reads a week of `git log` and writes the update a client
wants to read. Then `app/trace.py` checks each bullet against the commit it cites, and
`app/receipts.py` looks for the receipt it should have cited.

## The finding

The model rarely invents work. It **promotes** it:

| commit | the update said |
| --- | --- |
| `Pin requests<3` | "Refactored the code to pin `requests` to version **2.31.0**" — the commit *removes* 2.31.0 |
| `Run black` | "Implemented an `export_rows` function" — black reformatted it, `Add CSV export` wrote it |
| `Add retry to fetch_rate` | "Fixed a null check in `parse_invoice`" — right repo, wrong commit |
| `Document the retry behaviour` | "Implemented retry logic" — a README commit, claimed as implementation |
| `tests/test_empty.py` | "Added a test case (`test_empty_file`)" — a file that does not exist |

Every one of these is locally defensible. Collectively they are a lie, and nobody checks a
status report.

## What the gate is

Three deterministic rules over the cited commit — no model, no API call:

- **grounding** — numbers and identifiers in the sentence must appear in the commit, and a
  version that appears only in *deleted* lines counts as removed, not added
- **inflation** — the claim's leading verb is ranked against the commit message's leading
  verb; `refactored` on a `Pin` commit is two ranks apart
- **scope** — "the system" / "the platform" on a commit that touched one file

It is a **triage** tool, not a judge. It decides which sentences I read.

## What it measured

Two prompt variants, 3 runs each, 6 bullets per run — 36 bullets, on the same 12-commit
fixture repo.

- **13 bullets cited a commit that does not support them. The gate flagged all 13.**
- **4 more were wrong in a way it cannot see**: a commit that tweaked one constant
  (`0.2` → `0.25`) described as "introducing a retry mechanism". The verbs agree, so the
  verb rule passes it, and there is no number or filename to catch.
- Priming the prompt ("be literal, do not upgrade a verb") did not reliably reduce the flag
  rate — 7/18 vs 6/18 — but it did make the surviving bullets much more literal
  ("adjusted the sleep time to `0.25 * (attempt + 1)`" instead of "improved reliability").

The honest number is 17/36 wrong, and the gate catching 13 of them. Reading the **clean**
bullets is what found the other 4; a gate that only reports its own flags cannot find its
own misses.

## Run it

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
ollama serve &            # needs gemma3:4b
ollama pull gemma3:4b

# any local repo
PYTHONPATH=. .venv/bin/python scripts/report.py ~/code/some-client --limit 40

# the browser demo, from one saved run
PYTHONPATH=. .venv/bin/python scripts/build_demo.py
.venv/bin/uvicorn app.main:app --port 8077
```

`scripts/make_fixture_repo.py` builds the 12-commit demo repo, including two commits that
touch hundreds of lines and mean nothing and one that touches six lines and matters.

`scripts/check_gate.py` is the gate's own test set: twenty cases, each a sentence and the
commit it claims. Eleven must be flagged, nine must stay clean, and every case came from
reading real model output rather than designing the rules first.

```bash
PYTHONPATH=. .venv/bin/python scripts/check_gate.py    # 20/20
```

## What it does not do

- It cannot tell whether a sentence is *true about the code*. It checks that the receipt
  supports the sentence, not that the code works.
- It cannot catch the constant-tweak class of promotion (see above).
- The receipt suggestion compares commit messages and file names, not diffs, so it returns
  "no commit message explains this" rather than guessing when the fact lives only in a diff.
- Two Ollama details are load-bearing: use `/api/chat`, never `/api/generate`, and never
  send `format: "json"` — the grammar constraint collapses the output to `{}`.
