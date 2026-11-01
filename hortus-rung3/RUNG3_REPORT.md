# Hortus Rung 3 — real-simulation scorer prototype: report

Date: 2026-11-01. All numbers below are the actual output of `python3 -u run.py`
in this directory (full log kept in `run-output.txt`). Nothing is projected,
scaled, or hand-adjusted.

## Verdict up front

Yes — this scorer is fit to score **finalist** designs, with one guardrail:
keep the textbook formula for the wide evolutionary search and call the
simulation only on finalists. A scoring call costs ~40 s for a dense-fin
design on one CPU core with zero installs, which is fine for tens of
finalists and hopeless for thousands of candidates. Before trusting it for
selection (not just ranking), validate one simulated heatsink against a
measured rig or a commercial solver — this prototype has never met reality.

## Approach taken and why

Option 1 from the prompt: a finite-difference conduction solver written from
scratch (Python stdlib only — this machine has no numpy). One periodic fin
cell in 2D cross-section: aluminium base + centered fin, isothermal base
bottom (the stated 50 K difference), convection on every exposed face,
symmetry on the cell side walls, red-black SOR. Watts per metre of depth fall
out of the surface integral; multiply by depth and fin count.

Why this shape: it is the smallest model that still resolves the actual
bottleneck (conduction up the fin fighting convection off its sides) with no
black boxes. No Elmer/OpenFOAM: nothing was preinstalled and a 15-minute
install fight was explicitly out of scope.

## Verification (the solver earns trust here or nowhere)

Single fin, 0.745 mm x 60 mm, adiabatic tip, against the closed-form 1D fin
formula q = M·tanh(mL) (exact for this case):

| grid (vertical) | simulated | analytic | error | energy balance | iters |
|---|---|---|---|---|---|
| 0.50 mm | 180.139 W/m | 181.659 W/m | **0.84%** | 2.0e-3 | 20323 |
| 0.25 mm | 180.916 W/m | 181.659 W/m | **0.41%** | 2.0e-3 | 15993 |

Halving the grid halves the error — textbook convergence, not luck. Energy
books balance (heat out vs heat in through the base) to 2e-3 in every run.
Two bugs were found and fixed during verification (heat counted through air
cells; grid rounding the fin narrow) — both are documented here precisely
because verification caught them, which is the process working as designed.

## Champion vs reference (forced air, base 50 K over ambient)

Footprint 100 mm x 100 mm x assumed depth 100 mm for both (the genome omits
footprint; this is Assumption 1).

| design | h used | watts at dT=50 K | time per scoring call |
|---|---|---|---|
| champion (40 fins, 60 mm, 0.745/1.494 mm) | 55.9 (own channels) | **733.8 W** | ~42 s |
| reference (10 fins, 10 mm, 2/5 mm) | 12.3 (own channels) | **18.3 W** | ~8 s |

Sensitivity with a flat h=50 for both: champion **685.6 W**, reference
**74.0 W**. The ranking never wavers — champion beats reference by 9x–40x
under every assumption set. The formula's pick survives first contact with
physics.

## Every assumption, plainly

1. Footprint 100x100 mm (genome omits it). Depth direction = 100 mm of channel.
2. Aluminium k=180 W/mK (mid-range; pure Al can hit 237, alloys sit ~167).
   Conductivity barely matters here (fins are highly efficient either way).
3. Air 2 m/s along the channels (a small fan). h from laminar parallel-plate
   Nu=7.54 with D_h=2x spacing, fully developed — conservative (entrance
   effects would raise real h). Re=468 (champion) / 2133 (reference): laminar OK.
4. Base bottom uniformly at +50 K (e.g. 75 C base, 25 C air). Uniform base
   temperature flatters the reference slightly (no spreading resistance modelled).
5. Ignored: radiation (~5% upside at these temps), contact resistance, tip
   burrs, dust, flow maldistribution, buoyancy at fan failure.
6. Grid: 0.1 mm across, 0.5 mm vertical; modelled fin widths within 0.6% of
   nominal (champion 0.7407 vs 0.745 mm — costs it ~1%, reported not hidden).

## Runtime per scoring call (decides where this fits)

Dense-fin design: ~40 s single-core (this machine). Sparse designs: seconds.
Verdict on fit: finalist judging (tens of designs, overnight batch) yes;
in-loop evolution scoring (thousands) no — keep the formula there.

## What it is still missing before selection trusts it

1. One date with reality: a measured prototype or a commercial-solver
   cross-check of at least the champion number.
2. A spreading-resistance model if future genomes vary base thickness a lot.
3. Radiation + entrance-length h for hot, slow-air corners.
4. Speed: numpy/JAX port or multigrid would cut the 40 s to seconds.

## Grid refinement (OC-031, added after first commit)

Doubled grid (dx 0.0926 to 0.0463 mm, dy 0.5 to 0.25 mm, 4x cells):
champion 733.8 W to **735.9 W (+0.28%)**. The run used all 80,000 iterations
(408 s) and reached balance 6.5e-3 against the 2e-3 stop rule — i.e. the
value is stable to under a third of a percent but the strict energy
criterion was not met on the fine grid (diminishing returns: the remaining
imbalance lives in slow-decaying modes, not in the wattage). Verdict
unchanged; if anything the base grid was already converged for ranking.

`python3 -u run.py` (stdlib only, tested on macOS system Python 3.9).
Deterministic: same inputs, same numbers, no randomness anywhere.

## How to reproduce

`python3 -u run.py` (stdlib only, tested on macOS system Python 3.9).
Deterministic: same inputs, same numbers, no randomness anywhere.
