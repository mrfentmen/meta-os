#!/usr/bin/env python3
"""Heatsink fin simulator for META OFFICINA (stage 1).

A real simulator function: physics and math in code, no model calls,
no LLM judging its own designs. It scores one parametric heatsink
design (straight rectangular fins on a flat base, aluminium) by its
thermal resistance, and reports whether the design is feasible under
the workshop's manufacturing and volume rules.

Model (steady state, natural convection, fixed base temperature):
  - Footprint is fixed: 50 mm wide x 50 mm deep.
  - One fin: cross-section A_c = t * L, perimeter P ~= 2 * L
    (thin edges neglected), so m = sqrt(h * P / (k * A_c))
    simplifies to sqrt(2 * h / (k * t)) — the depth cancels.
  - Fin efficiency (adiabatic tip): eta = tanh(m * H) / (m * H).
  - Heat per fin: q_fin = eta * h * (2 * H * L) * dT.
  - Exposed base: q_base = h * (W * L - N * t * L) * dT.
  - Total heat q = N * q_fin + q_base; thermal resistance R = dT / q.
  - Lower R is better. R is quoted in degC/W.

Feasibility (a design that breaks a rule is a recorded failure,
not a silent drop — its score is still computed and kept):
  - Every parameter inside its declared range.
  - Fin gap (W - N * t) / (N - 1) >= 1.0 mm, so air can move
    between fins.
  - Total volume (base + fins) <= 100,000 mm^3 (100 cm^3).

Units: parameters arrive in millimetres and counts; the physics
runs in metres, watts, and kelvin. Nothing here touches the network,
the bus, or a model.
"""

import math
from dataclasses import dataclass

K_ALUMINUM_W_MK = 205.0
FOOTPRINT_W_MM = 50.0
FOOTPRINT_L_MM = 50.0
VOLUME_BUDGET_MM3 = 100_000.0
MIN_GAP_MM = 1.0

# Declared parameter ranges (stage 1 artefact class).
# Widened 2026-11-01 (boss's order): at the original bounds the
# volume rule was dead on the loop path — the largest gap-feasible
# volume was ~95,400 mm^3 (N=13, t=2.9, H=40, base=8) against the
# 100,000 mm^3 budget, so no feasible start could ever reach a
# volume violation and the volume repair move could never fire.
# Fin height 40 -> 80 and base thickness 8 -> 12 make volume-only
# violations reachable inside the ranges (max gap-feasible volume
# is now ~180,800 mm^3), so the rule and its repair move are live.
FIN_HEIGHT_MM = (5.0, 80.0)
FIN_THICKNESS_MM = (0.5, 3.0)
FIN_COUNT = (4, 30)
BASE_THICKNESS_MM = (2.0, 12.0)


@dataclass(frozen=True)
class HeatsinkParams:
    """One parametric heatsink design. All lengths in millimetres."""

    fin_height_mm: float
    fin_thickness_mm: float
    fin_count: int
    base_thickness_mm: float

    def as_dict(self):
        return {
            "fin_height_mm": self.fin_height_mm,
            "fin_thickness_mm": self.fin_thickness_mm,
            "fin_count": self.fin_count,
            "base_thickness_mm": self.base_thickness_mm,
        }


@dataclass(frozen=True)
class Conditions:
    """Cooling conditions for one simulation run."""

    h_w_m2k: float = 10.0  # natural convection
    t_base_c: float = 80.0
    t_amb_c: float = 25.0

    @property
    def dt_k(self):
        return self.t_base_c - self.t_amb_c


@dataclass(frozen=True)
class SimResult:
    """The scored outcome of one simulation. Score IS r_th_c_per_w."""

    params: HeatsinkParams
    conditions: Conditions
    r_th_c_per_w: float
    heat_w: float
    fin_efficiency: float
    volume_mm3: float
    gap_mm: float
    feasible: bool
    violations: tuple

    def as_dict(self):
        return {
            "params": self.params.as_dict(),
            "conditions": {
                "h_w_m2k": self.conditions.h_w_m2k,
                "t_base_c": self.conditions.t_base_c,
                "t_amb_c": self.conditions.t_amb_c,
            },
            "r_th_c_per_w": self.r_th_c_per_w,
            "heat_w": self.heat_w,
            "fin_efficiency": self.fin_efficiency,
            "volume_mm3": self.volume_mm3,
            "gap_mm": self.gap_mm,
            "feasible": self.feasible,
            "violations": list(self.violations),
        }


def fin_efficiency(m_per_m, height_m):
    """Adiabatic-tip fin efficiency for m * H (dimensionless)."""
    mh = m_per_m * height_m
    if mh <= 0:
        return 1.0
    return math.tanh(mh) / mh


def simulate(params, conditions=None):
    """Score one design. Never raises on a bad design: bad designs
    come back infeasible, with their violations named and their
    score still computed, so the failure ledger stays complete."""
    conditions = conditions or Conditions()
    if conditions.h_w_m2k <= 0 or conditions.dt_k <= 0:
        raise ValueError("conditions need h > 0 and t_base > t_amb")
    violations = []
    lo, hi = FIN_HEIGHT_MM
    if not lo <= params.fin_height_mm <= hi:
        violations.append("fin_height_mm outside [%s, %s]" % (lo, hi))
    lo, hi = FIN_THICKNESS_MM
    if not lo <= params.fin_thickness_mm <= hi:
        violations.append("fin_thickness_mm outside [%s, %s]" % (lo, hi))
    lo, hi = FIN_COUNT
    if not lo <= params.fin_count <= hi:
        violations.append("fin_count outside [%s, %s]" % (lo, hi))
    lo, hi = BASE_THICKNESS_MM
    if not lo <= params.base_thickness_mm <= hi:
        violations.append("base_thickness_mm outside [%s, %s]" % (lo, hi))

    # Metres for the physics.
    h_m = params.fin_height_mm / 1000.0
    t_m = params.fin_thickness_mm / 1000.0
    b_m = params.base_thickness_mm / 1000.0
    w_m = FOOTPRINT_W_MM / 1000.0
    l_m = FOOTPRINT_L_MM / 1000.0
    n = params.fin_count
    dt = conditions.dt_k
    h = conditions.h_w_m2k

    m = math.sqrt(2.0 * h / (K_ALUMINUM_W_MK * t_m))
    eta = fin_efficiency(m, h_m)
    q_fin = eta * h * (2.0 * h_m * l_m) * dt
    a_exposed = w_m * l_m - n * t_m * l_m
    q_base = h * a_exposed * dt
    q_total = n * q_fin + q_base
    r_th = dt / q_total if q_total > 0 else float("inf")

    volume_mm3 = (
        FOOTPRINT_W_MM * FOOTPRINT_L_MM * params.base_thickness_mm
        + n * params.fin_thickness_mm * FOOTPRINT_L_MM * params.fin_height_mm
    )
    gap_mm = (
        (FOOTPRINT_W_MM - n * params.fin_thickness_mm) / (n - 1)
        if n > 1
        else FOOTPRINT_W_MM
    )
    if gap_mm < MIN_GAP_MM:
        violations.append(
            "fin gap %.3f mm below minimum %.3f mm" % (gap_mm, MIN_GAP_MM)
        )
    if volume_mm3 > VOLUME_BUDGET_MM3:
        violations.append(
            "volume %.1f mm^3 above budget %.1f mm^3"
            % (volume_mm3, VOLUME_BUDGET_MM3)
        )

    return SimResult(
        params=params,
        conditions=conditions,
        r_th_c_per_w=r_th,
        heat_w=q_total,
        fin_efficiency=eta,
        volume_mm3=volume_mm3,
        gap_mm=gap_mm,
        feasible=not violations,
        violations=tuple(violations),
    )
