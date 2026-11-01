# Hortus rung 3 — thermal simulation scorer (NB-001)

Prototype from OPENCODE_PROMPT_HORTUS_RUNG3.md. Stdlib only, no installs.

Run (from this directory):

    python3 -u run.py

What it does: verifies a 2D fin-cell conduction/convection solver against
the closed-form single-fin formula, then scores the rung-1 champion vs the
reference block under identical forced air. All numbers print to stdout;
the full log of the reference run is kept next to this file.

Entry points: `solver.py` (`solve_cell`, `analytic_fin`), `run.py`.
Closeout verdict and assumptions: RUNG3_CLOSEOUT.md.

## Cost: seconds per scoring call (NB-008)

Measured on this Mac (Apple silicon, one core, Python 3.9 stdlib):

| case | coarse grid | fine grid |
|---|---|---|
| rung-1 champion (40 tall fins) | 42 s (omega 1.7) / 12 s (omega 1.9) | 408 s cap, unmet (1.7) / 215 s, met (1.9) |
| rung-2 8175 | 177 s (1.7, cap, bal 3.0e-3) | — |
| 78901 (48 x 100 mm) | 80 s (1.7) | — |
| reference block | 7.6 s (geo h) / 0.9 s (flat h=50) | — |
| single-fin verification | 39 s / 62 s (two dy) | — |

Omega 1.9 converges ~3.5x faster than 1.7 to the same answer (NB-006:
champion fine grid passes the 2e-3 balance rule at 42,395 iters).
Price of a future evolution scoring call: tens of seconds per dense
design — finalists only, never in-loop.
