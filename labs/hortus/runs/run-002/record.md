# Hortus run-002 — breeding record (OC2B-301–OC2B-306)

Branch: opencode2/500. Engine read-only (`hortus/*.py`, `breeding.py` untouched).
Entry-point map: see `labs/hortus/runs/run-001/record.md` §1 (same engine, same entry points).

## Definition — written BEFORE the run (OC2B-301)

Change vs run-001: exactly ONE variable — population size 20 → 40.
Everything else identical to run-001: 8 generations (CSV gens 1–8),
same mutation rule (Gaussian 8% + uniform crossover + tournament 3 +
elite 2, shipped bounds), same fitness measure
(`model.score` on nominal `TRAIN_ENV`), same verifier (default held-out
envs), same seed.

- Seed: 500001 (same seed isolates the population-size change).
- Driver: `run.py` in this directory (copy of run-001's with POPULATION_SIZE=40 only).

Seed line: SEED=500001. Changed variable: POPULATION_SIZE 20 → 40.

## Results (OC2B-302–OC2B-306)

The fitness curve rises in every generation with no flats and no dips:
best 56.5857 → 115.7830, mean 27.6415 → 92.8765, both monotone across
gens 1–8. The larger population found a better final best (115.7830) than
run-001's 108.8352 from the same seed — the one changed variable paid off
within the 8-generation budget.

| gen | best       | mean      |
|-----|------------|-----------|
| 1   | 58.813853  | 27.641530 |
| 2   | 71.080357  | 40.639465 |
| 3   | 71.232293  | 47.277843 |
| 4   | 87.426602  | 62.067531 |
| 5   | 92.235431  | 68.081545 |
| 6   | 100.917301 | 74.818277 |
| 7   | 113.039187 | 84.035955 |
| 8   | 115.783012 | 92.876514 |

Figure: `fitness.svg` (OC2B-304).

Selection (OC2B-306): run-002 selected for tall thin many-fin area inside
the mass cap — 33 fins at 60.0 mm, 0.81 mm fins on a lean 2.03 mm base,
0.391 kg feasible, and the champion PASSED the held-out gate
(`verified-candidate`: feasible and beating the reference in all three
held-out envs). Same seed as run-001, different fate: the extra population
bought a feasible champion.

- Reproduction (OC2B-305): clean-directory re-run from seed 500001,
  byte-identical `generations.csv`, identical winner hash
  0f95218be2a816f6236c70fda929a62d8d58ad16e3dbb16ca9c4e2f6cbf85092.
  Comparison: identical.
- Winner: `winner.json` — organism 318, genome
  [33.316094, 60.0, 0.811459, 2.027775], genome sha256 0f95218b…85092.
- CSV: 8 data rows, generations 1–8, no gaps (`check_csv.py`).
- Wall time: wall_seconds=0.01 (see `walltime.txt`).
- Errors (OC2B-322): no errors during the filed run; no reruns — one
  single clean run produced this pack.

## Pack hash

pack-sha256: e0b3dfe1974bd23e5f98bd9b6d795db10ad047405933f50533e14a407a091467
(Filed in `pack.sha256`; same zeroed-line procedure as run-001.)
