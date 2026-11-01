# Hortus rung 3 — closeout (NB-010)

## What rung 3 now proves

1. A from-scratch finite-difference fin-cell solver matches the closed-form
   single-fin answer to 0.41% (h=55.8 stated; halving the grid halves the
   error; energy balanced to 2e-3). File: oc-proofs/nb-002-verify.txt.
2. The rung-1 champion scores 733.8 W at dT=50 K forced air; the reference
   block 18.3 W under identical conditions. Ranking is assumption-proof
   (9x–40x across h treatments).
3. The rung-2 calibrated champion (organism 8175, base 1.400 mm) scores
   735.5 W — within 0.2% of rung-1's 733.8 W. Calibration moved the number
   by less than the grid error: the two champions are thermally tied.
4. The wide-genome champion (organism 78901, 48 x 100 mm fins) scores
   713.0 W — but its 100 mm height is OUTSIDE the calibrated geometry
   range, so that number is an extrapolation, stated here, not hidden.
5. Cost is measured, not guessed (README table): tens of seconds per dense
   design — finalist judging only.

## What it still does not prove (rung 4 and a boss decision)

No simulated number here has met a physical heatsink or a commercial
solver. Selection hardware still needs one measured cross-check.

## Exact commands to reproduce everything in this section

From `hortus-rung3/` (stdlib only, macOS system Python 3.9):

    python3 -u run.py                        # verification + champion vs reference
    python3 -u nb_batch.py                  # 8175, 78901, 5-geometry table
    # NB-006 fine-grid pass (omega 1.9, 42,395 iters, bal 2.0e-3):
    python3 -u -c "from solver import solve_cell;
    r=solve_cell(pitch=0.0025, fin_t=0.000745, base_t=0.001494, fin_h=0.060,
      dx=0.0025/54, dy=0.00025, h=55.9, k=180.0, theta=50.0,
      omega=1.9, max_iter=120000)"
    python3 -m pytest tests/queue-python/ -q  # (section B, throwaway only)

Determinism: champion coarse case run 3x, byte-identical watts and iters
(oc-proofs/nb-009-determinism.txt).
