"""Hortus Rung 3 — reproduce every number end to end:  python3 -u run.py.

1. Verification: single fin vs the closed-form 1D fin formula (adiabatic
   tip, exact match expected), at two grid resolutions + energy balance.
2. Scoring: champion vs reference heatsink under identical conditions.
"""
import math
import time

from solver import solve_cell, analytic_fin

# ---- stated assumptions (also recorded in RUNG3_REPORT.md) ----
K_ALU = 180.0        # W/mK, mid-range aluminium
THETA = 50.0         # K, base 50 K above ambient (e.g. 75 C base, 25 C air)
DEPTH = 0.100        # m, assumed 100 mm x 100 mm footprint
AIR_V = 2.0          # m/s fan flow along the channels
K_AIR = 0.026        # W/mK
NU_AIR = 1.5e-5      # m2/s
NU_CHANNEL = 7.54    # laminar fully-developed parallel-plate Nusselt
DX = 0.0001          # m, across-fin grid step
DY = 0.0005          # m, vertical grid step (fine: profile varies gently)


def channel_h(spacing):
    """Forced-air h from laminar channel flow (D_h = 2 * spacing)."""
    dh = 2.0 * spacing
    return NU_CHANNEL * K_AIR / dh


def reynolds(spacing):
    return AIR_V * 2.0 * spacing / NU_AIR


print("== 1. verification: single fin vs analytic (adiabatic tip) ==", flush=True)
VT = {"fin_t": 0.000745, "length": 0.060}
# dx picked so the fin width lands on whole cells (kills stair-step error)
VT_DX = VT["fin_t"] / 8
for dy in (DY, DY / 2):
    h_v = 55.8
    t0 = time.time()
    r = solve_cell(pitch=VT["fin_t"] + 0.010, fin_t=VT["fin_t"], base_t=0.0,
                   fin_h=VT["length"], dx=VT_DX, dy=dy, h=h_v, k=K_ALU,
                   theta=THETA, tip="adiabatic")
    a = analytic_fin(THETA, h_v, K_ALU, VT["fin_t"], VT["length"])
    err = abs(r["watts_per_m"] - a) / a * 100
    print(f"dy={dy * 1000:.2f} mm  sim={r['watts_per_m']:.3f} W/m  "
          f"analytic={a:.3f} W/m  err={err:.2f}%  "
          f"fin modelled={r['fin_width_modelled'] * 1000:.4f} mm  "
          f"balance={r['balance_err']:.1e}  iters={r['iters']}  "
          f"{time.time() - t0:.1f}s", flush=True)
print(flush=True)

print("== 2. scoring: champion vs reference (forced air, dT=50 K) ==", flush=True)
GEOMS = {
    # dx per case lands the fin width on whole cells (see report)
    "champion": {"fins": 40, "fin_h": 0.060, "fin_t": 0.000745, "base_t": 0.001494,
                 "dx": 0.0025 / 27},
    "reference": {"fins": 10, "fin_h": 0.010, "fin_t": 0.002, "base_t": 0.005,
                  "dx": 0.0002},
}
WIDTH = 0.100
for name, g in GEOMS.items():
    pitch = WIDTH / g["fins"]
    spacing = pitch - g["fin_t"]
    h_geo = channel_h(spacing)
    t0 = time.time()
    r = solve_cell(pitch=pitch, fin_t=g["fin_t"], base_t=g["base_t"],
                   fin_h=g["fin_h"], dx=g["dx"], dy=DY, h=h_geo, k=K_ALU, theta=THETA)
    dt = time.time() - t0
    watts = r["watts_per_m"] * DEPTH * g["fins"]
    fin_mm = r["fin_width_modelled"] * 1000
    bal = r["balance_err"]
    print(f"{name}: pitch={pitch * 1000:.3f} mm spacing={spacing * 1000:.3f} mm "
          f"Re={reynolds(spacing):.0f} h={h_geo:.1f} W/m2K", flush=True)
    print(f"  -> {watts:.1f} W at dT=50 K  (fin modelled={fin_mm:.4f} mm, balance {bal:.1e}, "
          f"{r['iters']} iters, {r['cells']} cells, {dt:.1f} s per scoring call)",
          flush=True)

print(flush=True)
print("== sensitivity: uniform h=50 W/m2K for both ==", flush=True)
for name, g in GEOMS.items():
    pitch = WIDTH / g["fins"]
    t0 = time.time()
    r = solve_cell(pitch=pitch, fin_t=g["fin_t"], base_t=g["base_t"],
                   fin_h=g["fin_h"], dx=g["dx"], dy=DY, h=50.0, k=K_ALU, theta=THETA)
    dt = time.time() - t0
    watts = r["watts_per_m"] * DEPTH * g["fins"]
    print(f"{name}: -> {watts:.1f} W  ({dt:.1f} s/call)", flush=True)
