# Science Lab (Meta OS world: `os/worlds/science-lab/`)

A small, honest laboratory that runs a full discovery cycle -- from a
question to a filed, verified repository record -- with every result
carrying its evidence level (0-6) and its provenance. A result is
shown at the level its record holds, never higher.

## What it is

Six systems from the LABORATORY design text (`PACK.md`, `pack.json`):

1. Research Intelligence (`literature.py`) -- sourced briefs; unpinned
   statements are dropped, contradictions marked contested.
2. Scientific Reasoning (`reasoning.py`, `reasoning_chain.py`) --
   hypotheses with falsifiers, pre-registered analysis, required
   critic.
3. Computational Lab (`compute.py`) -- sandboxed runs, determinism
   checks, per-department runners, crash records, budgets.
4. Discovery Engine (`cycle.py`) -- phases 1-7 as a state machine
   over `records/ledger.jsonl`. Step 8 is silent in the source text
   (`STEP_8` marker, never a working phase); steps 9/10
   (wetlab/publication) are permanently human-gated.
5. Independent Verification (`verify.py`) -- blind re-run, comparison
   record, rotation enforcement, write gate.
6. Knowledge Repository (`repository.py`) -- filed rows queryable by
   level, department, agent, date.

Showable outputs (`export.py`): session exports, evidence colour
bands (0 grey, 1 blue, 2 green, 3 teal, 4+ amber human-only),
`labs/science-lab-review/index.html`, department summaries, board
counts, hashed archives. Regeneration: `python3
os/worlds/science-lab/export.py --all` and `--review`.

## How a cycle runs

```
question -> brief -> hypotheses -> cheap-computations -> critic
  -> verification -> sealing (-> human gates wetlab/publication)
```

Each transition files one ledger entry with its reason
(`cycle.transition`). Missing inputs block the transition and say
which (`can_transition`). Kill the driver mid-phase and
`recover_cycle` resumes from records with no duplicated phase.
Budgets stop the run with a receipt (`lab_config`).

A worked reproduction target ships with the tree: the Delaney (2004)
ESOL question in `reproduction_target.json`, the full example cycle
`records/cycles/CYCLE-EXAMPLE-001.json` (parked at the wetlab gate,
sealed phases 1-7), and a fresh dress-rehearsal question on held-out
rows in `records/examples/dress_rehearsal.json`. The drill in
`records/examples/failure_drill.json` shows a broken input being
refused, never faked.

## Where the records live

- `records/ledger.jsonl` -- the append-only hash-chained log.
- `records/cycles/` -- cycle state records (one JSON per cycle).
- `records/repository/` -- filed rows (`claims`, `experiments`,
  `cycles`, `sources` JSONL).
- `records/literature/`, `records/reports/`, `records/examples/` --
  briefs, one-page cycle reports, worked examples.
- `records/exports/` -- generated OS-facing JSON (sessions,
  `dept_summary.json`, `board.json`); regenerate, never hand-edit.
- `records/archive/` -- hashed per-cycle bundles (`ID.zip` +
  `ID.sha256`).
- `schemas/` -- the record shapes everything above must satisfy.
- `tests/science-lab/` (repo `tests/`) -- the green suite proving it.
