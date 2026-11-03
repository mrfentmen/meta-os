# Meta Nervus eval — first slice

Nervus was already hosted on main (agents/registry.json, nervus/hosted.mjs)
but eval/ had no nervus harness, so there was no Nervus baseline for
"whatever raises eval scores" to be measured against. This is that first
harness: an offline replay of committed records only.

## What it scores: stub honesty, not model performance

No model is loaded anywhere in this path, and nothing here is evidence
about a model. The harness checks that the committed Nervus records say
they are stubs, and that their numbers are the stub's own fixed values:

| source | what the harness reads |
|---|---|
| os-build/nervus/stub-ledger.jsonl | 65 stub records, 13 per operation, all stub:true, one stub hash, probe "stub-probe (no model)", source "STUB" |
| os-build/nervus/hosted-receipt.json | five stub operations, all ok, stub:true |
| nervus/dose-windows.json | source null, zones empty — no steer may be called measured |
| nervus/layer-curve.json | exactly four recorded points, no interpolation |
| os-build/layer1/r12/NERVUS_FACE_GAP.md | face feed gap named GAP with a STUB-banner requirement, not filled |
| agents/registry.json | nervus lane says STUB contract run, no model loaded |

## What it is not

- Not a model eval. There is no model to score; the day a real model run
  exists, its records belong in a new scenario set, not in this one.
- Not a fill for the face feed gap. NER-GAP-01 passes because the gap is
  NAMED honestly, not because a feed contract exists.
- Not a live run. The harness never runs nervus/hosted.mjs: that run
  appends five records to the ledger and rewrites the receipt with a
  fresh timestamp, so running it would move the records being scored.
  The adapter reads committed files only, and the read-only guard in
  adapter.test.mjs proves the ledger line count is unchanged by a run.

## How to run

```
node eval/nervus/run.mjs            # real records, exits 1 on any fail
node eval/nervus/run.mjs --baseline # label-only fixture, always exits 0
node --test eval/nervus/adapter.test.mjs
```

## Baseline: the label-only reader

A fixture that claims every record set is "stub" and reads nothing. It
passes exactly the two scenarios whose honest answer IS the label
(NER-STUB-01, NER-STUB-02) and fails every scenario that requires an
actual read: 2/10. A label is not a verification. The real run passes
10/10 by reading the records; see baseline-run-report.md for the
baseline table.

## Results (this slice, main af457ebd)

- Real run: 10/10 (exit 0).
- Baseline: 2/10 (the two label rows by chant).
- Adapter tests: 9/9.
- Caught in development: the first draft of NER-DELTA-01 carried a
  truncated after_hash copied from a terminal dump; the harness failed
  it 13/13 until the full 64-character hash from the ledger was used.
  That is the harness doing its job.
