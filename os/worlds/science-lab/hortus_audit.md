# Hortus interface audit (Section 7, Task 61)

Source: read from `hortus/engine.py`, `hortus/model.py`,
`hortus/verifier.py`, `hortus/records.py` (code, not docs).
Hortus was not modified for this audit. Date: 2026-11-02.

## engine.py — the genetic algorithm

Exposes:

- Constants: `ENGINE_NAME = "hortus"`, `ENGINE_VERSION = "0.1.0"`,
  `MODEL_ID = "hortus-toy-fin-v1"`, `EVIDENCE_LEVEL_CAP = 2`.
- `class Organism`: slots `id, genome, parents, born, score`.
  `genome` is a float tuple, `parents` a tuple of organism ids.
- `_mutate(rng, genome, sigma_fraction=0.08, gene_bounds=None)`:
  per-gene Gaussian perturbation, clamped to bounds.
- `_crossover(rng, genome_a, genome_b)`: uniform per-gene choice.
- `_tournament(rng, population, size=3)`: sample-3, keep max score.
- `run_evolution(records_path, seed=20261101, generations=300,
  population_size=48, env=None, elite_count=2, verify=True,
  held_out_envs=None, model_label=None, gene_bounds=None)`:
  full GA run. Generation 0 is the catalogue seed
  (`model.REFERENCE_GENOME`) plus uniform-random genomes; each
  generation scores, files a `generation` record, keeps
  `elite_count` survivors (filing `death` for the culled), and
  refills by tournament selection + crossover + mutation. Ends by
  verifying the champion (unless `verify=False`, used by tests)
  and filing `verdict` + `run_end`. Returns first/last best
  scores, champion genome/id, and the verdict. One
  `random.Random(seed)` drives everything, so a run reproduces
  exactly from its `run_start` record.

## model.py — the fitness function (analytic toy model)

Exposes:

- `GENE_BOUNDS`: 4 genes — fin count (2–40), fin height mm
  (4–60), fin thickness mm (0.4–4), base thickness mm (1–8).
- `TRAIN_ENV`: nominal aluminium/air environment the population
  evolves against (h = 10 W/m2K, mass cap 0.45 kg, spacing floor
  + margin ramp).
- `REFERENCE_GENOME = (10.0, 25.0, 1.5, 3.0)`: catalogue design
  the verifier uses as the bar to beat.
- `CALIBRATED_H_MULTIPLIER = 0.355161` (+ `CALIBRATION_PROVENANCE`,
  `calibrated_train_env()`, `calibrated_held_out_envs()`): one
  fitted global multiplier from 14 real heatsink datasheet rows;
  explicit opt-in, default scoring unchanged.
- Pure functions: `clamp_genome(genome)`, `geometry(genome, env)`
  (spacing, mass, hard-constraint flags), `heat_watts(genome,
  env)` (fin-efficiency textbook terms, no penalties),
  `score(genome, env)` (heat minus spacing-margin ramp and
  mass-over-cap penalties).

## verifier.py — the held-out gate (separate code path)

Exposes:

- `BEAT_MARGIN = 1.05`; `HELD_OUT_ENVS`: 3 environments the
  population never sees (forced-air h=28, still-air-hot,
  other-alloy), each with a TIGHTER spacing floor than training.
- `verify_champion(genome, reference=REFERENCE_GENOME,
  held_out_envs=HELD_OUT_ENVS)`: re-derives feasibility and raw
  heat per held-out env; passes only if the champion is feasible
  AND beats the reference by the margin in EVERY env. Returns
  `{passed, champion_status, beat_margin, reference_genome,
  checks}` where `champion_status` is `verified-candidate` or
  `rejected`. Passing never promotes anything up the ladder.

## records.py — the append-only run log

Exposes:

- `class RecordWriter(path)`: append-only JSONL, one object per
  line, flushed per record; context-manager support.
- Record kinds: `run_start, birth, death, generation, verdict,
  run_end` (documented in the module docstring).
- `load_records(path)`: JSONL back to a list of dicts.
- `reconstruct(records)`: rebuilds the family tree
  (`organisms` with parents/born/died/cause, `generations`,
  `final_population`, `champion_id`, `verdict`); raises
  `ValueError` on structurally incomplete logs (unborn parents,
  deaths of the unborn, organisms neither dead nor surviving).

## Breeding-integration note (UNIMPLEMENTED marker rule)

`breeding.py` imports `hortus.engine` when the caller's path allows
it and records the engine name, version, and evidence cap as
provenance. When Hortus is NOT importable, no Hortus call is
invented: `breeding.hortus_status()` returns
`{"available": False, "marker": "UNIMPLEMENTED", ...}` and variant
proposal proceeds on `reasoning.generate_hypotheses` alone. The
marker is the honest record of the gap, not a silent fallback.

## What the breeding engine can and cannot do (Task 70)

Hortus today is a complete, deterministic, honestly-capped
candidate generator for ONE toy problem: it breeds
straight-fin heatsink genomes against a closed-form thermal
model, logs every birth and death to a reconstructible JSONL
run record, and gates its champion through a separate
held-out-environment verifier that it cannot influence. What it
cannot do is anything outside that loop: it has no notion of
experiment plans, hypotheses, falsifiers, evidence levels above
2, the lab ledger, or the Knowledge Repository; its model is an
analytic textbook calculation (calibrated once against 14
datasheet rows, residual dominated by two tight-pitch profiles
it cannot represent), not physics truth; and its champion is a
filed prediction, never a discovery claim. The science-lab
breeding integration (`breeding.py`) therefore uses Hortus as
audited provenance — recording that its GA searches heatsink
genomes, not plan variants — while variant proposals come from
`reasoning.generate_hypotheses` (every variant carries a
falsifier), variant execution goes through `compute.py` (same
records, same budgets, no side door), and selection happens
only after results against a pre-registered rule.
