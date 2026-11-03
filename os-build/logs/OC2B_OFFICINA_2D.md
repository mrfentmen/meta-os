# Officina stage 2d record — workshop memory (OC2B-371)

## What it does

Append-only workshop record (labs/officina/workshop-memory.jsonl):
one JSON line per finished brief {seq, timestamp_utc, entry} with no
delete/clear API, so the oldest entry can never be silently dropped.
`recall_for_brief` hands the next brief the tail plus totals. Holds
5 entries: briefs a/b/c + builds 001/002, seq 1..5 contiguous.

Pinned: append+readback, two-sequential (second brief reads the
first), 50-entry oldest-present, honest-numbers outcome, missing
store reads empty. Corruption drill: a mid-entry truncation fails
clean with the line number, never partial data.

## What it never claims

- Memory is a log, not learning: recall shows history, it does not
  grade or steer the next brief.
- The window is bounded and says so; the store is not.
- A corrupt line is an error, not a skip.

## Registry/README proposals (OC2B-372 2d half — FOR PARENT: lift into status file §15)

- PROPOSE os/worlds/officina/PACK.md: parts list gains
  runtime/memory.py ("append-only outcomes the next brief reads").
- PROPOSE labs/officina/builds/README.md: one line naming
  workshop-memory.jsonl as the 2d store (README edit, not registry).
