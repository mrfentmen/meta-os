# OC2B-351 / 361 — 2c bounds: values read live from code

## Bounds (OC2B-351)

Read from os/worlds/officina/runtime/heatsink.py (widened 2026-11-01):

- FIN_HEIGHT_MM = (5.0, 80.0) — os/worlds/officina/runtime/heatsink.py:51
- BASE_THICKNESS_MM = (2.0, 12.0) — os/worlds/officina/runtime/heatsink.py:54

(Also live in the same file: FIN_THICKNESS_MM = (0.5, 3.0) line 52,
FIN_COUNT = (4, 30) line 53, gap floor MIN_GAP_MM = 1.0 line 40,
volume budget VOLUME_BUDGET_MM3 = 100000.0 line 39, class footprint
50.0 x 50.0 mm lines 37–38.) The 2c checker reads these names, never
a copy: pack_export.BOUNDS holds the same objects (pinned by
test_bounds_are_the_live_ranges with `assertIs`).

## Pack verdicts (OC2B-358–360)

    brief-a-pack.json: check ok=True, violations=[] (proven, R=1.7210)
    brief-b-pack.json: check ok=True, violations=[] (proven, R=1.7210)
    brief-c-pack.json: check ok=True, violations=[] (proven, R=1.8915, H capped at 25 mm)

## Clean-directory check (OC2B-361)

Bounds checker re-run over all three packs from a clean directory
(cwd /private/var/folders/.../T, packs read by absolute path, no
repo state imported):

    brief-a pack: ok=True violations=[]
    brief-b pack: ok=True violations=[]
    brief-c pack: ok=True violations=[]

Three verdicts, all pass, independent of the working directory.
