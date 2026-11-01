"""Hortus Rung 3 — standalone 2D fin-cell thermal solver (Python stdlib only).

Models one periodic fin cell of a straight-fin heatsink in cross-section:
a base slab with one centered fin, convection on every exposed surface,
isothermal base bottom (the stated temperature difference), symmetry
(adiabatic) on the cell side walls. Solved with red-black SOR.

Units: metres, kelvin (excess over ambient), watts. The 2D result is
watts per metre of heatsink depth; multiply by depth and fin count
for the full heatsink (see run.py).
"""

BOTTOM_DIRICHLET = True


def build_cell(pitch, fin_t, base_t, fin_h, dx, dy=None):
    """Return (nx, ny, solid, base_rows) for one periodic cell.

    solid[j][i] True where aluminium. Bottom base_t metres are the base
    slab; the fin sits centred on top. base_t=0 means fin only (used for
    the analytic verification case). dy defaults to dx; a coarser dy is
    accurate because fin temperature varies gently along its height.
    """
    if dy is None:
        dy = dx
    nx = max(3, int(round(pitch / dx)))
    ny = max(3, int(round((base_t + fin_h) / dy)))
    dxa = pitch / nx
    dya = (base_t + fin_h) / ny if ny else dy
    nbase = int(round(base_t / (base_t + fin_h) * ny)) if (base_t + fin_h) > 0 else 0
    nbase = min(max(nbase, 0 if base_t == 0 else 1), ny)
    fin_cols = max(1, int(round(fin_t / dxa)))
    i0 = (nx - fin_cols) // 2
    solid = [[False] * nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            if j < nbase:
                solid[j][i] = True            # base slab
            elif i0 <= i < i0 + fin_cols:
                solid[j][i] = True            # fin
    return nx, ny, solid, nbase, dxa, dya, fin_cols


def solve_cell(pitch, fin_t, base_t, fin_h, dx, h, k, theta,
               tip="conv", omega=1.7, tol=1e-6, max_iter=80000, dy=None):
    """Solve one cell. Returns dict with watts_per_m and diagnostics.

    tip: "conv" (real runs) or "adiabatic" (verification against the
    tip-adiabatic analytic fin formula).
    """
    nx, ny, solid, nbase, dxa, dya, fin_cols = build_cell(pitch, fin_t, base_t, fin_h, dx, dy)
    T = [[0.0] * nx for _ in range(ny)]
    for i in range(nx):
        T[0][i] = theta                        # isothermal base bottom
    # Initial guess: 1D analytic fin profile (exact for slender fins, so
    # SOR only has to clean up 2D end effects instead of crawling the
    # whole transient). Correctness is unaffected: any init converges to
    # the same unique steady state.
    import math as _math
    _m = _math.sqrt(h * 2.0 / (k * fin_t)) if fin_t > 0 else 0.0
    _Htop = base_t + fin_h
    if _m > 0 and _Htop > 0:
        _den = _math.cosh(_m * fin_h) if fin_h > 0 else 1.0
        for j in range(1, ny):
            _y = (j + 0.5) * dya
            _prof = theta * _math.cosh(_m * max(_Htop - _y, 0.0)) / _den
            for i in range(nx):
                if solid[j][i] and j >= nbase:
                    T[j][i] = _prof
                elif solid[j][i]:
                    T[j][i] = theta

    def is_air(j, i):
        if i < 0 or i >= nx:
            return False                       # side walls: symmetry, never air
        if j < 0 or j >= ny:
            return True                        # top/bottom exterior is air
        return not solid[j][i]

    # Face conductances (energy-balance discretization, exact for dx != dy):
    # x-faces have area dya and spacing dxa, y-faces area dxa spacing dya.
    wx = k * dya / dxa
    wy = k * dxa / dya

    # SOR update for one solid cell (skip the Dirichlet bottom row).
    def update(j, i, om):
        if j == 0:
            return 0.0
        num = 0.0
        den = 0.0
        # left / right: solid -> conduction; air -> convection;
        # outside the domain -> symmetry mirror (weight counts twice).
        for ii in (i - 1, i + 1):
            if 0 <= ii < nx and solid[j][ii]:
                num += wx * T[j][ii]
                den += wx
            elif 0 <= ii < nx:
                den += h * dya                  # air gap: convection
            else:
                num += wx * T[j][i]
                den += wx                        # symmetry mirror
        # down (j - 1 >= 0 always here; air below is impossible by geometry)
        if solid[j - 1][i]:
            num += wy * T[j - 1][i]
            den += wy
        else:
            den += h * dxa                      # exposed step facing down
        # up
        if j + 1 < ny and solid[j + 1][i]:
            num += wy * T[j + 1][i]
            den += wy
        elif j + 1 >= ny:
            if tip == "conv":
                den += h * dxa                  # fin tip convection
            # else adiabatic tip: mirror -> no net term
        else:
            den += h * dxa                      # exposed step -> convection
        new = num / den if den else T[j][i]
        old = T[j][i]
        T[j][i] = old + om * (new - old)
        return abs(T[j][i] - old)

    def heat_balance():
        qq = 0.0
        for j in range(1, ny):
            for i in range(nx):
                if not solid[j][i]:
                    continue
                if i - 1 >= 0 and not solid[j][i - 1]:
                    qq += h * dya * T[j][i]
                if i + 1 < nx and not solid[j][i + 1]:
                    qq += h * dya * T[j][i]
                if j + 1 < ny and not solid[j + 1][i]:
                    qq += h * dxa * T[j][i]
                elif j + 1 >= ny and tip == "conv":
                    qq += h * dxa * T[j][i]
        qi = 0.0
        if ny > 1:
            for i in range(nx):
                # Heat can only enter through solid: air columns of the
                # Dirichlet row sit at theta but conduct nothing.
                if solid[1][i]:
                    qi += k * dxa * (T[0][i] - T[1][i]) / dya
        return qq, qi

    it = 0
    bal = 1.0
    while it < max_iter:
        it += 1
        mx = 0.0
        for colour in (0, 1):                  # red-black ordering
            for j in range(1, ny):
                for i in range(nx):
                    if solid[j][i] and (j + i) % 2 == colour:
                        d = update(j, i, omega)
                        if d > mx:
                            mx = d
        # Update-size alone can stall far from steady state on slender
        # fins, so the stop rule also requires energy balance (heat out
        # vs heat in), checked every 200 sweeps to keep it cheap.
        if it % 200 == 0 or mx < tol * max(theta, 1.0):
            qq, qi = heat_balance()
            bal = abs(qq - qi) / max(qq, 1e-30)
            if mx < tol * max(theta, 1.0) and bal < 2e-3:
                break

    # Watts per metre depth: convection loss over every exposed face.
    # heat_balance also returns the base-bottom heat in, which must match.
    q, q_in = heat_balance()
    ncells = sum(row.count(True) for row in solid)
    return {
        "watts_per_m": q,
        "heat_in_per_m": q_in,
        "balance_err": abs(q - q_in) / max(q, 1e-30),
        "iters": it,
        "converged": it < max_iter,
        "cells": ncells,
        "fin_width_modelled": fin_cols * dxa,
        "dx": dxa,
    }


def analytic_fin(q_base_theta, h, k, t, length, adiabatic_tip=True):
    """Classic 1D rectangular-fin result (per metre depth, excess temp theta).

    q = M * tanh(m*L), M = theta*sqrt(h*P*k*A), m = sqrt(h*P/(k*A)),
    P = 2 (both sides, per metre depth), A = t*1. Exact only when the tip
    is adiabatic; compare with tip="adiabatic" solver runs.
    """
    import math
    p = 2.0
    a = t
    m = math.sqrt(h * p / (k * a))
    big_m = q_base_theta * math.sqrt(h * p * k * a)
    if adiabatic_tip:
        return big_m * math.tanh(m * length)
    lc = length + a / 2.0
    return big_m * math.tanh(m * lc)
