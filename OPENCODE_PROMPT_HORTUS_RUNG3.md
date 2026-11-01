# OpenCode task — Hortus Rung 3: a real simulation scorer (prototype, standalone)

You are building a standalone prototype in its own directory. You are NOT
editing the meta-os repo. Deliverable lands in:

    ~/workspace/hackathon/demo-stack/hortus-rung3/

## Why this exists

Meta Scientia's breeding engine (Hortus) evolves heatsink designs against a
scoring formula. Rung 1 was a textbook formula (labelled toy). Rung 2
(calibration against real datasheets) is being built separately. YOUR job is
rung 3: prove that a real physics simulation can score these designs, so the
formula can eventually be replaced by simulation for finalist designs.

## The target geometry

The current Hortus champion (rung-1 winner, organism 9086) is a straight-fin
heatsink defined by four numbers:

- fins: 40
- fin height: 60.0 mm
- fin thickness: 0.745 mm
- base thickness: 1.494 mm

The engine's genome omits the heatsink's overall width/length; for your
prototype, state an assumed footprint (e.g. 100 mm x 100 mm) in your report as
an explicit assumption. The reference design it beat is a plain low-fin block;
use 10 fins, 10 mm height, 2 mm thickness, 5 mm base on the same footprint as
the comparison case.

## What to build

A small, self-contained thermal simulation that takes a fin geometry and
returns watts dissipated at a stated temperature difference and airflow
condition. Acceptable approaches, in order of preference:

1. A finite-difference / finite-volume conduction+convection solver you write
   yourself (Python stdlib or numpy if available). This is preferred: no
   heavy installs, fully inspectable.
2. An installed open-source solver (Elmer, OpenFOAM) ONLY if it is already
   present or installs cleanly in under ~15 minutes. Do not burn the session
   fighting an installer. Fall back to option 1.

Non-negotiables:

- The solver must be VERIFIED before it is trusted: run it on a case with a
  known closed-form answer (a single fin, or a flat plate with a textbook
  solution) and report simulation vs analytic answer with % error.
- Then score BOTH the champion geometry and the reference geometry under the
  same conditions the formula used (forced air first). Report both numbers.
- State every assumption: airflow model, material conductivity (aluminium
  ~167-237 W/mK — say which you used), boundary conditions, mesh resolution,
  and what the solver ignores (radiation, contact resistance, etc.).

## Rules

- Real numbers from real runs only. If the solver does not converge or the
  verification fails, report that plainly — a failed prototype with an honest
  report is the deliverable in that case, not a success story.
- No changes outside the hortus-rung3 directory. Do not touch the repo, the
  bus, or any other lane's files.
- Work AFK: no questions. Make reasonable choices, document them, keep going.

## Deliverable

In ~/workspace/hackathon/demo-stack/hortus-rung3/:

- the solver code,
- a run script that reproduces your numbers end to end,
- RUNG3_REPORT.md containing: approach taken and why, the verification case
  (analytic vs simulated, % error), champion vs reference simulated watts,
  every assumption, runtime per scoring call (this decides whether simulation
  can score finalists only or more), and your honest verdict: is this scorer
  fit to replace the formula for finalist designs, and what is it still
  missing to be trusted.
