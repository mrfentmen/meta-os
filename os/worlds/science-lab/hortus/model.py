"""Hortus demo target: an analytic fin/heatsink toy model.

Hortus needs a fitness function that is real, deterministic code.
This module is that function for the shipped demo target: a
straight-fin heatsink on a flat base plate. The score is computed
by the closed-form model below. There is no learned component and
no model call anywhere in Hortus.

WHAT THIS MODEL IS, AND IS NOT
------------------------------
This is an ANALYTIC TOY MODEL. It is the standard textbook
straight-fin calculation (fin efficiency via tanh(mL)/mL with a
corrected tip length, overall surface efficiency, Newton's-law
cooling over the total area), reduced to a handful of closed-form
terms. It is honest as a demonstration fitness function: the same
genome always scores the same, and the trade-offs it contains
(more fin area versus worse fin efficiency versus more mass) are
the real trade-offs of the physical problem.

It is NOT physics truth and must never be cited as such. Its
assumptions, stated so a reader can see exactly where it departs
from a real heatsink:

1. Steady state, one-dimensional conduction along the fin height,
   uniform fin cross-section, no radiation.
2. A single uniform convective coefficient h over every surface
   (fins, exposed base, tips). Real h varies with position,
   orientation, and airflow, and is usually the least-known
   number in the whole problem.
3. Fin tips are handled with the corrected-length approximation
   (Hc = H + t/2) instead of an explicit tip boundary condition.
4. Fin surfaces are counted as 2 * depth * Hc per fin; the small
   fin end faces and base edges are ignored.
5. Material properties (k, rho) are constants from the
   environment record, not temperature-dependent.
6. The base plate is isothermal at delta_t above ambient (an
   infinite-spreading assumption); contact resistance is zero.
7. Fin spacing enters only as a feasibility floor (below it,
   closely spaced fins choke natural convection in reality; the
   model represents that whole phenomenon as a constraint plus a
   safety-margin penalty ramp, not as physics).

A champion of this model is a candidate design for the lab to
look at, at evidence ladder level 2 at most (computationally
tested, PACK.md). It is not a validated heatsink, and Hortus
never claims otherwise.

Units: SI throughout the calculation. Genomes are expressed in
millimetres for readability and converted here.
"""

import math

# Genome layout: (n_fins, fin_height_mm, fin_thickness_mm,
# base_thickness_mm). Bounds are the search space Hortus may use.
GENE_BOUNDS = (
    (2.0, 40.0),    # n_fins (rounded to int when scored)
    (4.0, 60.0),    # fin height, mm
    (0.4, 4.0),     # fin thickness, mm
    (1.0, 8.0),     # base plate thickness, mm
)

# Fixed plate footprint: fins stand across the width and run the
# full depth.
PLATE_WIDTH_M = 0.100
PLATE_DEPTH_M = 0.080

# The environment the shipped demo run evolves against.
TRAIN_ENV = {
    "name": "train-nominal",
    "h_w_per_m2k": 10.0,        # gentle forced air, assumed uniform
    "k_w_per_mk": 237.0,        # aluminium, nominal
    "rho_kg_per_m3": 2700.0,
    "delta_t_k": 40.0,
    "min_spacing_m": 0.0010,    # hard manufacturing/airflow floor
    "margin_spacing_m": 0.0018,  # below this, margin penalty ramps in
    "mass_cap_kg": 0.45,
}

# A sensible catalogue design, used by the verifier as the
# reference a champion must keep beating off its home turf.
REFERENCE_GENOME = (10.0, 25.0, 1.5, 3.0)

# --- Rung-2 calibration (2026-11-01) ---------------------------
# The shipped TRAIN_ENV coefficient h = 10 W/m2K is a nominal
# modelling choice, not a measurement. calibration/check_scorer.py
# compared this model's heat core against 14 real Wakefield
# Engineering bonded-fin heatsink configurations with measured
# natural-convection thermal resistances (calibration/
# datasheet_parts.json) and fitted ONE global multiplier on h,
# by least squares on percent error, over a 10-configuration
# calibration subset. The 4-configuration validation subset was
# never fitted against.
#
#   uncalibrated:  calibration mean error -64.5%, validation -62.9%
#   calibrated:    calibration mean error  -8.0%, validation  -3.9%
#                  (validation RMS error 6.3%, mean |error| 5.8%)
#
# Full tables and the honest caveats (the residual is dominated
# by two tight-pitch profiles whose fin-channel choking this
# model cannot represent): calibration/CALIBRATION.md.
#
# The multiplier is EXPLICIT and OFF by default: score() and
# heat_watts() are unchanged, TRAIN_ENV is unchanged, and the
# rung-1 demo run reproduces exactly as recorded. Callers opt in
# via calibrated_train_env() / calibrated_held_out_envs().
CALIBRATED_H_MULTIPLIER = 0.355161

CALIBRATION_PROVENANCE = {
    "fitted_on": "calibration subset of calibration/datasheet_parts.json",
    "parameter": "single global multiplier on h_w_per_m2k",
    "validation_rms_pct_error": 6.3,
    "validation_mean_abs_pct_error": 5.8,
    "report": "calibration/CALIBRATION.md",
}


def calibrated_train_env():
    """TRAIN_ENV with the rung-2 calibrated coefficient.

    Identical to TRAIN_ENV in every field except the name and
    h_w_per_m2k, which is scaled by CALIBRATED_H_MULTIPLIER
    exactly once.
    """
    env = dict(TRAIN_ENV)
    env["name"] = "train-nominal-calibrated"
    env["h_w_per_m2k"] = TRAIN_ENV["h_w_per_m2k"] * CALIBRATED_H_MULTIPLIER
    return env


def calibrated_held_out_envs():
    """The verifier's held-out environments with each h scaled
    by CALIBRATED_H_MULTIPLIER exactly once, so a calibrated run
    is judged in the same calibrated coefficient regime it was
    evolved in. Imported lazily to avoid a module cycle."""
    from . import verifier
    envs = []
    for env in verifier.HELD_OUT_ENVS:
        scaled = dict(env)
        scaled["name"] = env["name"] + "-calibrated"
        scaled["h_w_per_m2k"] = (
            env["h_w_per_m2k"] * CALIBRATED_H_MULTIPLIER)
        envs.append(scaled)
    return tuple(envs)


def clamp_genome(genome):
    """Clamp a genome into GENE_BOUNDS; n_fins stays a float here
    and is rounded only inside the scorer."""
    return tuple(
        min(max(float(g), lo), hi)
        for g, (lo, hi) in zip(genome, GENE_BOUNDS)
    )


def geometry(genome, env):
    """Derived geometry and feasibility facts for a genome.

    Pure function of (genome, env). Returns a dict with the fin
    gap (spacing), mass, and the two hard-constraint flags.
    """
    n_fins, height_mm, thickness_mm, base_mm = genome
    n = int(round(n_fins))
    t = thickness_mm / 1000.0
    if n >= 2:
        spacing = (PLATE_WIDTH_M - n * t) / (n - 1)
    else:
        spacing = PLATE_WIDTH_M
    volume = (
        PLATE_WIDTH_M * PLATE_DEPTH_M * (base_mm / 1000.0)
        + n * t * PLATE_DEPTH_M * (height_mm / 1000.0)
    )
    mass = env["rho_kg_per_m3"] * volume
    return {
        "n_fins": n,
        "spacing_m": spacing,
        "mass_kg": mass,
        "spacing_ok": spacing >= env["min_spacing_m"] - 1e-12,
        "mass_ok": mass <= env["mass_cap_kg"] + 1e-12,
    }


def heat_watts(genome, env):
    """Raw heat dissipation Q (watts) from the toy model, before
    any feasibility or margin penalty. Pure and deterministic."""
    n_fins, height_mm, thickness_mm, _base_mm = genome
    n = int(round(n_fins))
    t = thickness_mm / 1000.0
    height = height_mm / 1000.0
    h = env["h_w_per_m2k"]
    k = env["k_w_per_mk"]

    perimeter = 2.0 * (PLATE_DEPTH_M + t)
    cross_section = t * PLATE_DEPTH_M
    m = math.sqrt(h * perimeter / (k * cross_section))
    h_corr = height + t / 2.0
    eta_fin = math.tanh(m * h_corr) / (m * h_corr)

    a_fin = n * 2.0 * PLATE_DEPTH_M * h_corr
    a_base = PLATE_WIDTH_M * PLATE_DEPTH_M - n * t * PLATE_DEPTH_M
    a_total = a_fin + a_base
    eta_overall = 1.0 - (a_fin / a_total) * (1.0 - eta_fin)
    return h * eta_overall * a_total * env["delta_t_k"]


def score(genome, env):
    """Fitness: heat dissipation minus penalties.

    Penalties, all deterministic:
    - Spacing below the environment's safety margin is penalised
      on a linear ramp (30 W across the margin band) so evolution
      is paid to keep design margin instead of hugging the hard
      floor; below the hard floor the ramp continues and the
      design is also flagged infeasible by geometry().
    - Mass above the cap is penalised at 200 W per kilogram over.

    The verifier deliberately does NOT trust this number: it
    re-derives feasibility and raw heat under held-out
    environments (verifier.py).
    """
    geo = geometry(genome, env)
    q = heat_watts(genome, env)
    value = q
    margin = env.get("margin_spacing_m")
    if margin is not None and geo["spacing_m"] < margin:
        band = margin - env["min_spacing_m"]
        shortfall = margin - geo["spacing_m"]
        value -= 30.0 * (shortfall / band)
    if geo["mass_kg"] > env["mass_cap_kg"]:
        value -= 200.0 * (geo["mass_kg"] - env["mass_cap_kg"])
    return value
