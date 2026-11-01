"""Round 2 Section A batch: NB-004 (8175), NB-005 (78901), NB-007 (5-geo table).
Appends human-readable lines to nb007-table.txt. Run from hortus-rung3/:
  python3 -u nb_batch.py
"""
import time
from solver import solve_cell, analytic_fin
import math

K, TH, DEPTH = 180.0, 50.0, 0.100
DXC, DYC = 0.0001, 0.0005   # coarse grid (NB-007 solver column)


def chan_h(sp):
    return 7.54 * 0.026 / (2.0 * sp)


def analytic_full(fins, H, t, b, h):
    W = 0.100
    m = math.sqrt(h * 2 / (K * t))
    M = TH * math.sqrt(h * 2 * K * t)
    qfin = M * math.tanh(m * H)
    qbase = h * (W - fins * t) * DEPTH * TH
    return (qfin * fins * DEPTH) + qbase


def best_grid(pitch, t):
    """Pick nx (8..64) minimizing fin stair-step error; return (dx, cols)."""
    best = None
    for nx in range(8, 65):
        dx = pitch / nx
        cols = max(1, round(t / dx))
        err = abs(cols * dx - t) / t
        if best is None or err < best[0]:
            best = (err, dx, cols)
    return best[1], best[2]


def score(label, fins, H, t, b, note=""):
    pitch = 0.100 / fins
    h = chan_h(pitch - t)
    dx, _cols = best_grid(pitch, t)
    t0 = time.time()
    r = solve_cell(pitch=pitch, fin_t=t, base_t=b, fin_h=H, dx=dx, dy=DYC,
                   h=h, k=K, theta=TH)
    dt = time.time() - t0
    a = analytic_full(fins, H, t, b, h)
    watts = r["watts_per_m"] * DEPTH * fins
    line = ("%s: sim=%.1f W analytic=%.1f W diff=%+.1f%% h=%.1f fin=%.4fmm bal=%.1e iters=%d %.1fs %s"
            % (label, watts, a, (watts - a) / a * 100, h, r["fin_width_modelled"] * 1000,
               r["balance_err"], r["iters"], dt, note))
    print(line, flush=True)
    return line


if __name__ == "__main__":
    out = []
    out.append(score("NB-004 8175", 40, 0.060, 0.000745, 0.001400,
                     "(rung-2 calibrated; base 1.400 vs rung-1 1.494)"))
    out.append(score("NB-005 78901", 48, 0.100, 0.000405, 0.001000,
                     "(HEIGHT 100mm OUTSIDE calibrated range)"))
    out.append(score("NB-007a ref", 10, 0.010, 0.002, 0.005))
    out.append(score("NB-007b champ1", 40, 0.060, 0.000745, 0.001494))
    out.append(score("NB-007c mid", 20, 0.030, 0.001, 0.002))
    out.append(score("NB-007d tall", 60, 0.100, 0.0004, 0.001))
    out.append(score("NB-007e stubby", 5, 0.020, 0.003, 0.008))
    with open("nb007-table.txt", "a") as f:
        f.write("\n".join(out) + "\n")
