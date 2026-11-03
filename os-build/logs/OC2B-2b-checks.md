# OC2B-339 / 340 / 341 — 2b checks: dedup, timings, offline drill

## Dedup check (OC2B-339)

`find_duplicate_sources` (normalised, case/whitespace-folded) over
each note's full source list:

    brief-a: no duplicates ([])
    brief-b: no duplicates ([])
    brief-c: no duplicates ([])

No source is cited twice under different titles in any note.

## Latency record (OC2B-340)

Timed wall-clock around the 2b run (2a loop + repo grep + note
build) and the 2c pack emit, per brief, on Del's Mac 2026-11-02:

    brief-a note: 0.0068 s — pack: 0.0001 s (proven, 4 rounds, R=1.7210)
    brief-b note: 0.0055 s — pack: 0.0000 s (proven, 4 rounds, R=1.7210)
    brief-c note: 0.0030 s — pack: 0.0000 s (proven, 6 rounds, R=1.8915)

Raw numbers in labs/officina/builds/gen-timings.json. All offline,
no model calls, so these are pure code time.

## Failure drill (OC2B-341)

`search_web(query, offline=True)` refuses cleanly:

    RuntimeError: web search unavailable (offline drill): repo-only
    note or clean refusal — no cached web claims are invented

Degraded behaviour: the repo-only note still builds (search_repo +
shelf_limits disclose the gap; the SHELF_LIMITS line says coverage
is shelf + repo, nothing more). No refusal of the whole 2b step is
needed — the note stays honest about what it could not check.
Pinned by test_offline_refuses_clean in
tests/officina/test_oc2b_prior_art.py.
