# Meta Aegis eval — first slice

Aegis had no eval harness. Ignis, Medicus, and Vigiles have one.
This is Aegis's first: a small offline replay of committed records.

## What it scores

Five scenarios, all from records already in the repo:

| id | what it replays | recorded value it must match |
|---|---|---|
| AEG-KEV-01 | KEV cross-check over the committed findings file | KEV.json run kev-2026-11-02: checked 0, flagged 0, unchecked 0, 10 non-sweep excluded |
| AEG-LED-01 | findings ledger summary | 10 records: info 2, low 4, medium 4 |
| AEG-DIFF-01 | sweep diff mechanics | SWEEP_DIFF.json: 0 added, 0 removed, 5 distinct keys unchanged (see quirk below) |
| AEG-FP-01 | false-positive drill, re-run in a temp dir | FALSE_POSITIVE_DRILL.md: 3 clean packages, 0 findings, status ran |
| AEG-PARSE-01 | sweep prose parse, the one positive detection | tests/aegis-sweep.test.mjs S3 shape: one hit, ahash 0.8.12, RUSTSEC-2024-0001 |

No live OSV call, no live KEV fetch, no model call, no CVE invented.
The committed findings carry no CVE, so the KEV scenario honestly
expects zero checked — the catalog rows themselves are not committed,
only their counts, so the replay runs against an empty catalog.

## What the numbers mean

A passing replay means the code still reads its own records the same
way. It does not mean the tree is clean, and it does not rate live
detection: the only positive detection here is a committed prose shape,
not a live advisory. Detection metrics cover the three detection
scenarios only (KEV, FP drill, parse); the ledger and diff scenarios
are replays, not detections, and sit outside those metrics.

## Run it

```
node eval/aegis/run.mjs              # real modules, exits 1 on any replay miss
node eval/aegis/run.mjs --baseline   # always-no-detection fixture; sets the bar
node --test eval/aegis/adapter.test.mjs
```

The baseline passes the two no-detection scenarios and fails the
positive detection plus both replays. That gap is the bar: a real run
must beat it by replaying all five.

## Quirk the replay exposes

The recorded diff run says before 7, after 7, unchanged 5. That is not
a replay miss: the diff keys a finding by target plus title, and the
7-record snapshot held duplicate pairs, so 7 records collapse to 5
keys. Unchanged counts keys, before/after count records. The eval
records this as-is; changing the diff's counting is a separate lane
decision, not something this harness quietly fixes.
