# Hortus run-003 — breeding record (OC2B-307, OC2B-311–OC2B-312)

Branch: opencode2/500. Engine read-only (`hortus/*.py`, `breeding.py` untouched).
Entry-point map: see `labs/hortus/runs/run-001/record.md` §1 (same engine, same entry points).

## Definition — written BEFORE the run (OC2B-307)

Change vs run-001: the fitness measure (NOT the mutation rule). Fitness is
now `model.score` on the rung-2 CALIBRATED training env
(`model.calibrated_train_env()`: h scaled by 0.355161, validated RMS error
6.3% vs datasheet parts) instead of nominal `TRAIN_ENV`. Verifier uses the
matching calibrated held-out envs (`model.calibrated_held_out_envs()`) so
the champion is judged in the regime it evolved in. Population back to 20,
mutation rule / crossover / tournament / elite / bounds all unchanged.

- Seed: 500001 (same seed isolates the fitness-measure change).
- Driver: `run.py` in this directory (copy of run-001's with USE_CALIBRATED=True only).

Seed line: SEED=500001. Changed variable: fitness env TRAIN_ENV → calibrated TRAIN_ENV.

## Results (OC2B-308–OC2B-312)

The fitness curve rises fast then saturates: best 17.3494 → 38.0218 by
generation 6 and flat afterwards (best unchanged gens 6–8, mean slipping
30.5756 → 29.9611). Not falling, but converged early — the calibrated
low-h fitness (absolute scores ~3x lower than nominal) stops paying for
novelty after gen 6 within this budget. A plateau, reported as a plateau.

| gen | best      | mean      |
|-----|-----------|-----------|
| 1   | 19.087496 | 9.834073  |
| 2   | 23.334363 | 17.413845 |
| 3   | 27.873670 | 18.669591 |
| 4   | 33.624105 | 21.018723 |
| 5   | 35.671448 | 25.405772 |
| 6   | 38.021775 | 30.575623 |
| 7   | 38.021775 | 30.509664 |
| 8   | 38.021775 | 29.961053 |

Figure: `fitness.svg` (OC2B-310). Note the y-axis scale differs from runs
001/002: calibrated scores are watts under a ~3x smaller h, so cross-run
score comparison is meaningless — only shapes and verdicts compare.

Selection (OC2B-312): run-003 selected for fewer taller fins on a lean
base under the calibrated low-h fitness — 28 fins at 60.0 mm, 1.05 mm
fins, 2.54 mm base, 0.437 kg feasible; the champion PASSED the calibrated
held-out gate (`verified-candidate`).

- Reproduction (OC2B-311): clean-directory re-run from seed 500001,
  byte-identical `generations.csv`, identical winner hash
  54c2e7cae76016ec71c9a84ef5a061d46ba1faed07572110828c99a9583728ec.
  Comparison: identical.
- Winner: `winner.json` — organism 124, genome
  [28.035793, 60.0, 1.052935, 2.540562], genome sha256 54c2e7ca…3728ec.
- CSV: 8 data rows, generations 1–8, no gaps (`check_csv.py`).
- Wall time: wall_seconds=0.01 (see `walltime.txt`).
- Errors (OC2B-322): no errors during the filed run; no reruns — one
  single clean run produced this pack.

## Pack hash

pack-sha256: fbb8d2e79c5384f5851633de2bc00fd7dadde99bed3c190a8bf23a5934154c04
(Filed in `pack.sha256`; same zeroed-line procedure as run-001.)
