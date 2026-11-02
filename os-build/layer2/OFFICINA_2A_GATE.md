# Officina stage 2a acceptance gate (BUILD WAVE W3, Milo)

Stage 2a, from `os-build/BUILD_WAVE_2026-11-02.md`: rough-words
intake plus the self-building brief — an agent iterates its own
brief, with a decision log carrying reasons — proven on the
heatsink class. Milo writes the acceptance gate first; the 2a
build itself goes to the first free builder lane and is announced
on room 1 when it starts. Stages 2b/2c/2d stay sequenced behind
this gate.

## The gate

Run from the repo root:

```
python3 os-build/officina_2a_gate.py
```

Exit 0 only if every clause passes. Stdlib only, offline, no
model calls, no network, no bus posts. The only grader is code:
the heatsink simulator plus the independent held-out gate.

| Clause | What it proves |
| ------ | -------------- |
| G1 intake | Fresh rough words parse to a structured brief: artefact class heatsink-fin-geometry, the stated target recorded as stated, unstated slots (e.g. power) in unknowns and never invented, ungradeable wishes (e.g. compact) kept as preferences, explicitly not graded. |
| G2 self-iteration | The loop runs with no human in the loop and ends proven; the decision log has exactly one entry per round, rounds sequential from the round-0 intake guess, every entry carrying rule, decision, and reason, every round >= 1 carrying the grade that motivated it. |
| G3 held-out independence | The held-out gate re-run from the final parameters agrees with the record's verification: fresh score recomputed (never trusted), held-out score feasible and under the 2.0 degC/W bar. |
| G4 brief's own target | Proven requires meeting the brief's stated target, not just the workshop bar — a design stalling above a tighter stated target is never proven. |
| G5 negative + export | An impossible target ends unproven and exports with proven=false; a proven design exports with proven=true and its verification attached. Nothing unproven is ever dressed up as proven. |
| G6 suite | The existing Officina test suite (`tests/officina`) passes on the branch under test. |

The gate uses fresh held-out wording, not one of the recorded
runs in `os/worlds/officina/runs/` — it must pass on words it was
not written against, not on a replay.

## What PASS does and does not mean

PASS means the 2a loop behaves as specified in code: intake is
honest about what the words state, iteration is logged and
rule-driven, and only held-out-verified designs count as proven.

PASS does NOT mean: a part validated against a measured physical
heatsink (the simulator has never been checked against measured
hardware); a run on a booted Meta OS image or as a scheduled
service (the loop has never run there); or an intake parser
checked against real user wording beyond the tested examples.
Those limits are stated in `os/worlds/officina/PACK.md` and stand
until a later stage closes them. Every score this gate prints is
SIMULATED.

## Status on this branch

Gate script + this spec, branch `milo/build-wave-w3` off
origin/main. Gate run quoted in the room-1 completion post, never
inherited from another branch. No merge from this branch — Pax
merges at checkpoints.
