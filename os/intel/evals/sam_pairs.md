# STR-003 eval: SAM evaluation set, Alerts panel pairs

## What was built

`intel/evals/sam/` now holds the first SAM eval pairs from Milo's
lane: the intel-alerts dashboard panel in its two ground-truth
states, desktop + phone.

- Good (build-ok): fresh renders of the all-quiet panel — zero alerts
  fed, live watchdog beat 30s old, panel reading "All quiet —
  watchdog alive" (rendered by `intel/sam_render.py`, Playwright +
  the repo's cached Chromium, the DSH-030/DSH-035 method; the script
  asserts panel text and harness snapshot at render time, and the
  desktop shot was also confirmed visually).
- Bad (build-broken): byte-identical copies of the DSH-030
  submission shots of the same panel fed the DSH-037 dev-pack alerts
  payload — five critical open alerts from one `watchdog.tick` on a
  stall/collision/dead-dep fixture (presence-stall milo:1, three
  file-collisions on `intel/status.py`, dead-dep 9:3).

Manifest `pairs.json` carries the labels and the ground-truth basis
per half; `intel/sam_check.py` enforces manifest shape, PNG magic,
the bad halves' alert ids against the dev-pack payload, and
byte-identity of the firing copies against the submission originals.

## Check results

- `python3 intel/sam_render.py intel/evals/sam` — both quiet renders
  PASS (alerts 0, beat alive, quiet text present, zero page errors).
- `python3 intel/sam_check.py` — PASS (see suite run below).
- Pinning tests: `tests/test_intel_sam_eval.py`, 6 tests.

## NOT proven here

No SAM verdict exists for these files and none is claimed; the
STR-001/GOV-007 stretch gate has not opened (Nov 1 checkpoint), so
this set is built early on the STR-002/STR-005 precedent, not as a
gated approval. The shots are fixture renders, not live mid-drill
captures, and no demo-machine listening check (DEM-018) is claimed.
