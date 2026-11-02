# Aegis sweep diff — mechanics proof

Run `sweep-diff-2026-11-02T14-40-17-947Z`. Before: `/tmp/findings-before.jsonl` (7 findings). After: `os-build/aegis/findings.jsonl` (7).

| delta | count |
|---|---|
| added | 0 |
| removed | 0 |
| unchanged | 5 |

**Empty diff.** The machinery ran end to end and the two runs agreed. That is the expected
result for the same tree swept twice the same day; it is not evidence that the tree is clean.
## What this does not claim

- A removed finding is not a fixed one: it may be a version bump, a changed source, or a
  different query answer. The records say what was seen, not why it moved.
