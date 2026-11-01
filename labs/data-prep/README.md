# labs/data-prep/ — eval footage tooling (NC-171..NC-183)

Each tool, its command, its fixture, its measured throughput.

- `extract.py` — video in, JPEG frames out: `python3 extract.py VID DIR
  --fps 2` (names `<base>-tSS.sss.jpg`) or `--scene THRESH` (frame-diff
  mode). Fixture: 5 s testsrc + moving white block → 10 frames at 2 fps,
  order asserted. Throughput: 19.2 frames/s on this Mac.
- `sheet.py` — contact sheet: `python3 sheet.py OUT.png F... --cols 4`
  (file name under each frame). Fixture: 12 frames → 4x3 sheet, labels
  viewed legible.
- `phash.py` — dHash dedupe: `python3 phash.py F...` (hamming ≤ 6);
  `--aug` adds flip-detection. Fixture: 3 wild originals + recompressed
  copies → exactly 3 groups; flipped copy flagged, other scene not.
  Throughput: 120.3 frames/s.
- `manifest.py` — JSONL manifest (file, source, timestamp, hash,
  content-derived group id): `python3 manifest.py DIR OUT.jsonl`.
  Re-run after deleting a frame reports `GAP: <file>`, never renumbers.
- Tests: `node --test labs/data-prep/tests/dataprep.test.mjs` — 6/6.
  Needs python3 (+PIL), ffmpeg. Fixtures are synthetic (no datasets
  fetched, per the task).
