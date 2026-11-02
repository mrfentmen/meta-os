# Python judge — behaviour record (B233)

Module: `server/queue/judge.py`. Read 2026-11-02. Every claim below
cites the file and line range it comes from. This record describes the
code as written; it does not change it.

## What it does

The judge is the second agent in the Imperium loop: patrol flags a
frame, the judge weighs two independent readings of the same frame, and
rules `confirmed`, `cleared`, or `inconclusive` (`judge.py:1-27`).
A confirmed ruling routes the package to the owning service's SIMULATED
endpoint (`judge.py:40-47`).

## Inputs

- `service_route(division)` — one division string (`judge.py:50-53`).
- `combine(division, first_category, review_category, review_ok,
  is_flagged)` — two categories, the review's success flag, and the
  caller's flagged-category predicate (`judge.py:56-76`).
- `build_judge_prompt(division, first_result, review_result)` — the two
  agents' full result objects (`judge.py:79-104`).
- `parse_verdict(text)` — the judge model's raw reply (`judge.py:111-131`).

## Outputs

- `service_route` → `{"service": ..., "path": ...}` for the three known
  divisions, `None` otherwise (`judge.py:40-53`).
- `combine` → `(verdict, reasons)` where reasons is a list of plain
  strings for the incident timeline (`judge.py:56-76`).
- `build_judge_prompt` → one newline-joined string; the readings are
  serialised with `json.dumps` and cut to their first 1200 characters
  (`judge.py:101-102`).
- `parse_verdict` → `(verdict, category, reasons)`; reasons is always a
  list of strings (`judge.py:111-131`).

## The ruling order (the part that matters)

1. Review failed (`review_ok` false) or carried no category →
   `inconclusive`; the judge never confirms on a missing reading
   (`judge.py:63-67`).
2. Review category is not flagged → `cleared`, with the
   "look-alike" reason (`judge.py:68-71`).
3. Review category equals the patrol category → `confirmed`
   (`judge.py:72-74`).
4. Otherwise the review independently flagged a different category →
   `confirmed`; two flagged readings stand over one (`judge.py:75-77`).

## Refusals

- Unknown division: no route, `None`, "never guess a service"
  (`judge.py:50-53`).
- Missing/failed review: `inconclusive`, never `confirmed`
  (`judge.py:63-67`).
- Reply is not JSON → `inconclusive`, reason "the judge's reply was not
  JSON" (`judge.py:116-118`).
- Reply is JSON but not an object → `inconclusive`
  (`judge.py:119-121`).
- Verdict word outside `confirm`/`reject`/`investigate` → `inconclusive`
  and the offending value is quoted in the reason (`judge.py:122-126`).
- `reasons` is not a list → `[]`, never a crash (`judge.py:127-129`).

The three model words map to the three internal verdicts
(`judge.py:107-108`): `confirm` → `confirmed`, `reject` → `cleared`,
`investigate` → `inconclusive`.

## Finding

- `parse_verdict` passes `category` through with no type check
  (`judge.py:130`). A list or object category is returned as-is; the
  caller must validate it before it reaches a record. Reported, not
  fixed, because a judge reply's category is the model's output and the
  contract boundary belongs to the caller.
