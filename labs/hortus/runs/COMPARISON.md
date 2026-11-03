# Hortus runs 001–003 — comparison (OC2B-313–OC2B-315, OC2B-318–OC2B-319, OC2B-323–OC2B-324)

Engine read-only throughout (`hortus/*.py`, `breeding.py` unedited).
All three runs: 8 generations, seed 500001, same mutation rule
(Gaussian 8% + uniform crossover + tournament-3 + elite-2). Scores are NOT
comparable across the fitness change (run-003's calibrated watts are ~3x
smaller by construction); shapes and verdicts compare.

## 3-run table (OC2B-313)

| run | variable changed vs run-001 | final best | curve shape |
|-----|-----------------------------|------------|-------------|
| 001 | baseline (pop 20, nominal fitness) | 108.8352 | steep rise all 8 gens; one small mean dip at gen 7 |
| 002 | population 20 → 40 (ONE variable) | 115.7830 | monotone rise, best and mean, no flats or dips |
| 003 | fitness measure → calibrated low-h env | 38.0218 | rise gens 1–6, then plateau (best flat gens 6–8, mean slipping) |

## Diversity (OC2B-314)

Metric: mean pairwise Euclidean distance in bounds-normalized genome
space — each gene scaled 0–1 by its `model.GENE_BOUNDS` range (max
possible distance 2.0 for 4 genes). Computed from `records.jsonl`: gen-0
births vs final-population genomes.

| run | gen-0 diversity (mean / min / max) | final diversity (mean / min / max) |
|-----|------------------------------------|------------------------------------|
| 001 | 0.7305 / 0.1756 / 1.2498 | 0.2233 / 0.0490 / 0.4307 |
| 002 | 0.7579 / 0.1090 / 1.3517 | 0.2103 / 0.0231 / 0.4729 |
| 003 | 0.7305 / 0.1756 / 1.2498 | 0.2257 / 0.0649 / 0.4822 |

(Runs 001 and 003 share gen-0 numbers: same seed, same population size,
same initial draw.)

## Premature-convergence check (OC2B-315)

Collapse rule: YES iff final mean pairwise distance < 0.05 (near-clones).

- run-001: NO collapse — final 0.2233, min pair 0.0490, best still improving at gen 8.
- run-002: NO collapse — final 0.2103, min pair 0.0231, best and mean rising at gen 8.
- run-003: NO collapse by the metric (final 0.2257) — but selection converged in score: best flat gens 6–8. Diversity without improvement: the population kept spreading while the optimum stopped moving.

## Pack hashes (OC2B-318)

- run-001: adc4c6306d57c254aa402827662be74ffbc49a59d04709b56d106d871102cb63
- run-002: e0b3dfe1974bd23e5f98bd9b6d795db10ad047405933f50533e14a407a091467
- run-003: fbb8d2e79c5384f5851633de2bc00fd7dadde99bed3c190a8bf23a5934154c04

(Each in `<run>/pack.sha256` with its per-file table; zeroed-line procedure
documented in the manifest header.)

## CSV parse check (OC2B-323)

`python3 labs/hortus/runs/run-001/check_csv.py` output:

```
run-001/generations.csv: OK, 8 data rows (generations 1-8)
run-002/generations.csv: OK, 8 data rows (generations 1-8)
run-003/generations.csv: OK, 8 data rows (generations 1-8)
all three CSVs parse; total data rows: 24
```

## Suite tails (for the §12/§13 status blocks)

Post-run Hortus suite `(cd os && python3 -m unittest discover -s tests -p "test_hortus*.py")`:

```
..............
----------------------------------------------------------------------
Ran 14 tests in 0.120s

OK
```

(Identical to the pre-run baseline: 14 passed, 0 failed.)

Post-run science-lab suite `(python3 -m unittest discover -s tests/science-lab)` from repo root:

```
Ran 170 tests in 1.036s

OK
```

(§1 baseline was 163; +7 = this file's `test_oc2b_hortus.py`. No failures.)

## Errors (OC2B-322)

- run-001: two `run.py` crashes on SVG string formatting during
  development, before any filed output existed; partial outputs deleted;
  the pack is one single clean run. No generation errored.
- run-002: no errors during the filed run; no reruns.
- run-003: no errors during the filed run; no reruns.

## Compute time (OC2B-324)

walltime.txt per run: 0.01 s + 0.01 s + 0.01 s = 0.03 s total compute
across the three runs (pop ~20–40, 8 gens: small by design).

## Breeding chapter — what Hortus demonstrably does, in 5 lines (OC2B-319)

1. Hortus breeds heatsink genomes against a fixed deterministic scorer and logs every birth, death, and generation to append-only JSONL.
2. Eight generations at pop 20–40 visibly move best and mean fitness under selection pressure on a fixed seed.
3. Every run reproduces bit-for-bit from its seed in a clean directory (CSVs byte-identical, winner hashes identical).
4. The held-out verifier gate bites: run-001's mass-infeasible champion was rejected while run-002/003's feasible champions passed.
5. Hortus output is a candidate at ladder level 2 at most — never a discovery claim, never physics truth.
