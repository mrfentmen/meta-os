# OC2B-406 patrol wiring check

`server/queue` was NOT edited (Pax's lane). This run exercises
`models.py` exactly the way patrol would after a flag, in a scratch
config: the snapshot is read from the staged file
`test-footage/frames/ignis-fire-2.jpg` (252,107 bytes, standing in for
the `fetch_snapshot` seam), then `models.segment()` is invoked with a
patrol-style prompt.

Run log:

- staged snapshot: 252107 bytes
- `models.segment(frame, "segment the flagged subject (burning vehicle)
  for the patrol record")`
- result: `ValueError: SAM output carried no <|box;...|> segment`
  (Responses call itself succeeded — receipt written, 1468 ms,
  `images_processed: 1`; the output text was empty)
- degraded path (the honest one): patrol files the flag WITHOUT a
  measured region; the reading's own region stands. No region was
  invented.

Segment record produced: none (no-box). Receipt: scratch file
`receipts-wiring.jsonl` (copied into `OC2B-model-receipts-index.md`).

Note: the same frame returned a box under the OC2B-403 prompt minutes
earlier — see `VARIANCE.md`. The wiring path handles both outcomes;
this run happened to exercise the no-box branch.
