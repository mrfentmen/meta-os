# OC1B-442/443/444/449 — README fixes, re-run confirmations, badge check, verdict

Tree derived on: 3452d244 (fresh clone /tmp/oc500-baseline). Fix commit: 01f8c264 on opencode/500-s1 (README.md only, 9 lines).

## OC1B-442 — README diff (quoted from `git diff 94010c76..01f8c264 -- README.md`)

- Badge node: `2071 run, 2016 passing` -> `2071 run, 2015 passing`
  (URL `...node%20tests-2071%20run%2C%202015%20passing...`).
- Badge rust: `2186 passing` (green) -> `workspace does not build` (red)
  (URL `.../rust%20tests-workspace%20does%20not%20build-red`).
- Table Node row: `2071 run, 2016 pass, 55 fail` -> `2071 run, 2015 pass, 56 fail`.
- Table Rust workspace row: `2186 pass, 0 fail` -> `does not build on this
  tree (intel tests fail to compile: E0063)`. Command column unchanged.
- Table queue row: `296 pass, 1 skip` -> `296 pass, 0 skip`.
- Table intel row: `186 of 186 lib tests pass; b10_parity 53 of 53` ->
  `does not compile (E0063 missing field 'spec'), 0 tests run`.
- Node-failures paragraph: `The 55 Node failures are one known set` ->
  `The 56 Node failures are the known native-mirror set ... plus one
  docs-index gap: R11-282 fails because WAVE2-branch-boot-serial.txt is
  committed but not named in BOOTLOG_INDEX.md`.
- Built-with Rust row: `2186 tests green` -> `workspace green excluding
  intel (intel tests do not compile: E0063)`.
- Kernel size (2 occurrences): `about 5,800 lines across 13 files` ->
  `about 6,000 lines across 13 files` (measured 5,984).
- NOT touched (STALE named, fix owned elsewhere — see underived list):
  Goose 33 programs / 1,253 checks (cited record now says 59 drivers /
  2,715 assertions; replacing the quoted run_native receipt needs a §16
  re-run, so the receipt quote is left for §16/Pax), services count 25,
  OS-side 122,000, batch-2 100/42/46 numbers, musica "4 of 4",
  model-endpoint history claims.

## OC1B-443 — re-run confirmations after the fix commit

- `npm test` fresh re-run: tests 2071, pass 2015, fail 56 — matches the
  fixed table row. Full output: os-build/logs/OC1B-readme-node-rerun.txt.
- `python3 -m unittest discover -s tests/queue-python` fresh re-run:
  Ran 296 tests, OK, 0 skipped — matches the fixed row.
- `cargo test --workspace` fresh re-run: exit 101, same E0063 intel
  compile errors, 0 tests run — matches the fixed row's "does not build".
- `wc -l kernel/src/*.rs` unchanged: 5,984 total / 13 files — matches
  "about 6,000 ... 13 files".

## OC1B-444 — badge check

- node badge SVG renders `2071 run, 2015 passing` (curled 2026-11-02).
- rust badge SVG renders `workspace does not build` (red).
- worlds badge SVG renders `12 of 12 valid` (unchanged, still true).
Badge text == shield URL parameters in all three.

## OC1B-449 — section verdict

README numbers are now VERIFIED-or-STALE-fixed for every number this lane
could re-derive; the underived list below is the verdict's remainder.
STALE-fixed: node row + badge, queue row, rust workspace row + badge +
built-with row, intel row, kernel line count (2x), node-failures paragraph.
STALE-named-not-fixed (needs a code run or a Pax ruling, not a number edit):
Goose 33/1,253 receipt block (§16 re-run), services count 25
(24 manifest rows vs 37 source dirs).
UNVERIFIABLE-ON-MAC (named, never padded): OS-side ~122,000 (method
unstated; reconstructions 119,098 with os/intel scope / 139,496 with full
os scope), batch-2 100/42/46/0 + 6.4s + 100-of-100 (no eval log in repo;
in-repo audit os-build/README_AUDIT_BOND.md agrees), musica "4 of 4"
(no such suite in tree; actual tests/musica-*.test.mjs = 39 pass),
model endpoint history (no model_receipts.jsonl in tree; live re-proof is §9),
Rust 2186-origin (no passing number exists on this tree; replaced by the
proven 1851-excl-intel + does-not-build state).
