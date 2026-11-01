# META OFFICINA world pack: invention workshop

Status: **PARTIAL.** The design loop, heatsink simulator, and held-out
acceptance gate are built and tested; every other declared watcher
remains definition only. The manifest (`pack.json`, checked by
`os/worlds/validate_pack.py`) and this document are the definitions;
no runtime code in this pack runs a real manufacturing line, orders
a build, or ships a part.

## Runtime status (what runs, honestly)

- RUNS: `os/worlds/officina/runtime/heatsink.py` — the heatsink fin
  simulator. Straight rectangular aluminium fins on a flat base,
  scored by thermal resistance from fin-efficiency physics in code.
  Pinning-tested. It has never been validated against a measured
  physical heatsink: its numbers are simulated, and every surface
  that shows them must say so.
- RUNS: `os/worlds/officina/runtime/design_loop.py` — the
  design-job loop. Post, claim, score, complete or fail with a
  reason; winners kept by score; held-out acceptance gate;
  overnight-style run recording and best-proven-design export.
  Pinning-tested. It has never run on a booted Meta OS image or
  as a scheduled service.
- DOES NOT RUN: anything that builds, orders, or ships a physical
  part. A "workshop-proven" design is a simulation result that
  cleared the held-out gate, not a manufactured and measured part.
- RECORDED RUN: `os/worlds/officina/runs/overnight-run-001.json`
  (240 variants, seed 20261101) and its export
  `os/worlds/officina/runs/overnight-best-design.json`. The raw
  best design (R 0.8987) FAILED held out — its fin gap falls below
  minimum under manufacturing tolerance — and was not exported as
  proven. The exported design is the second winner (R 1.1835),
  which cleared the gate. That is the gate working, not failing.

## Purpose

The invention workshop: an agent that designs, simulates, breaks,
and redesigns — thousands of iterations a night. Stage 1 runs one
concrete artefact class, heatsink fin geometry, because its physics
fits in code: fin efficiency, heat dissipation, volume and gap
rules, all checkable without a model in the loop. No LLM ever
judges a design here. The simulator scores; the loop counts; the
gate re-scores held out. A human decides whether anything gets
built.

## Stage 2a: rough words in, proven design out

A user gives a sloppy plain-words description — no blueprint, no
specs. `runtime/brief.py` turns it into a structured brief
(artefact class, stated requirements, stated targets, preferences,
unknowns, conflicts), then iterates the brief itself with no human
in the loop: each round grades the current parameters, applies
exactly one rule-driven move (gap repair, volume repair, range
repair, improvement, held-out repair), and logs the decision with
its reason and the grade that motivated it.

Honesty rules, same as stage 1: the parser is rules in code, not
a model, so it records only what the words state — anything
unstated goes in unknowns (a workshop default target is labelled
a default in targets and disclosed as a gap in unknowns, never
passed off as stated). Wishes the simulator cannot grade (cheap,
small) are preferences, explicitly not graded. The search grades
at design conditions, but nothing counts as proven until the
independent held-out gate passes — and proven also requires the
brief's own target, so a design that stalls above a tighter stated
target is never exported as proven. Worked run
`runs/rough-words-run-001.json`: "a heatsink for a hot little
chip, about 50mm square, no fan, keep it small, under 2 degrees
per watt" — 4 rounds, 3 logged improvements, accepted with
R 1.7210 (held-out 1.1848), exported to
`runs/rough-words-best-design.json`.

Stage 2a gate fixes (ML-001, ML-003): a stated forced-airflow
requirement now flows into grading — fan-cooled briefs grade at
h=25, never at the passive h=10, and the held-out gate re-scores
under the same design conditions (its fixed h=15 then acts as a
degraded-airflow check for forced briefs). Worked run
`runs/forced-airflow-run-001.json`: "cool a power supply in a
hot garage, fan is fine, cheap" — 2 rounds, accepted with
R 1.0623 at h=25 (held-out 1.7825). And when the best improving
move is blocked by a gap or volume rule, the loop now tries a
gap/volume move whose two-step outcome beats the current grade
instead of stalling — worked run `runs/gap-headroom-run-001.json`:
height capped, add fins gap-blocked, a gap-headroom thin-fins move
fires, then add fins fires, accepted with R 1.3405. UNPROVEN,
stated plainly:
the intake parser has never been checked against real user
wording beyond the tested examples, and the loop has never run
on a booted Meta OS image or as a scheduled service.

## What it watches

- **design-board**: design jobs — posted, claimed, scored, kept as
  winners, or failed, in job order.
- **simulator-bench**: simulator runs — the physics score of every
  variant and every held-out re-score, with the conditions each
  score was computed under.
- **failure-ledger**: failures — every variant that broke a rule,
  with its score and its named violation, so a failed design is
  never silently dropped.
- **proven-record**: workshop-proven designs — which designs
  cleared the held-out gate, their scores, and the files they were
  exported to.

## Agent roster

- **design-smith**: samples variants, posts jobs, keeps winners.
- **brief-smith**: turns rough plain words into a structured
  brief, then iterates the brief itself, logging every decision
  with its reason; never grades its own work — the held-out gate
  decides what counts as proven.
- **bench-runner**: runs the simulator on every job and re-score.
- **failure-clerk**: records every failure with its score and reason.
- **record-keeper**: keeps the proven record; never marks proven
  what the gate did not pass.
- **workshop-herald**: the pack's only cross-world messenger. It
  sends proven-design summaries (id, artefact class, score, export
  path) to the crew and nothing else.

## Alerts (shared wire format)

- `design-proven` (warning, routine, summary, crosses the bus):
  a design cleared the held-out gate. Carries id, artefact class,
  score, export path.
- `design-failed` (warning, routine, local): a variant broke a
  rule. Carries id, score, named violation.
- `held-out-mismatch` (warning, routine, local): a design failed
  the held-out gate. Carries id and which check failed.

## Privacy classes

- `local_only`: full variant parameters for unproven designs,
  failure details beyond the named violation, held-out parameter
  sets and tolerance factors, full score curves and job-by-job
  records.
- `bus_summary`: proven design id, artefact class, score, export
  file path; run counts (variants run, failures recorded, designs
  proven).

## Cross-world messages

- SENDS to crew (`design-proven-summary`): proven design id,
  artefact class, score, export file path. It never carries full
  variant parameters, held-out parameter sets, or failure details.
- RECEIVES from crew (`design-request`): artefact class and design
  constraints for a requested run.

## Firstboot config

- `workshop_name` (required): workshop name for this installation.
- `artefact_focus` (optional): artefact class this workshop
  iterates on.
- `operator_contact` (required): operator contact.
- `room_name` (required): bus room this installation joins.

## Urgency classes

- 1, life-safety: a design failure that would endanger a user if
  the part were built as drawn. Preempts everything else.
- 2, urgent: a held-out gate failure on a design already
  exported as proven. Act before the export is used.
- 3, routine: design proven, design failed, run-completion notes.
- 4, digest: sealed overnight run records and score curves.

## Honesty label

Design aid only. It proposes, scores, and records designs. It
never orders a build, never ships a part, and never presents a
simulated score as a measured result. A design counts as
workshop-proven only after the held-out re-score passes, and even
then a human decides whether anything gets built. The stage-1 bar
(R <= 2.0 degC/W at design conditions and held out) is a chosen
workshop threshold for this 50x50 mm aluminium sink, not a law of
physics; the run record names it so the number stays honest.
