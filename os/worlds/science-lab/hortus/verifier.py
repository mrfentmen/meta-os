"""The Hortus verifier gate: champions are re-scored off home turf.

The generator (engine.py) and this verifier are separate code
paths on purpose (PACK.md: the generator never verifies its own
work). The verifier receives a genome and the reference design —
never the run's narrative, scores, or generation history — and
re-derives everything from model.py primitives under HELD-OUT
environments the population was not evolved against:

- a stronger airflow (higher h) that punishes tall thin fins
  whose efficiency was flattered by the training coefficient,
- weaker airflow at a larger temperature difference,
- a different alloy (lower k),
- and in every held-out environment, a TIGHTER fin-spacing
  floor than training used, so a design that wins by hugging
  the training constraint boundary is caught.

A champion passes only if, in EVERY held-out environment, it is
feasible (spacing and mass constraints hold there) and still
dissipates at least BEAT_MARGIN times the reference design's
heat. Passing this gate does not promote anything up the
evidence ladder: it makes the genome a verified CANDIDATE.
Per PACK.md, a Hortus output is capped at ladder level 2 and
files as a prediction; ladder promotion belongs to the lab's
independent verifier, not to this gate.
"""

from . import model

BEAT_MARGIN = 1.05

HELD_OUT_ENVS = (
    {
        "name": "heldout-forced-air",
        "h_w_per_m2k": 28.0,
        "k_w_per_mk": 237.0,
        "rho_kg_per_m3": 2700.0,
        "delta_t_k": 40.0,
        "min_spacing_m": 0.0015,
        "margin_spacing_m": None,
        "mass_cap_kg": 0.45,
    },
    {
        "name": "heldout-still-air-hot",
        "h_w_per_m2k": 6.0,
        "k_w_per_mk": 237.0,
        "rho_kg_per_m3": 2700.0,
        "delta_t_k": 55.0,
        "min_spacing_m": 0.0015,
        "margin_spacing_m": None,
        "mass_cap_kg": 0.45,
    },
    {
        "name": "heldout-other-alloy",
        "h_w_per_m2k": 14.0,
        "k_w_per_mk": 167.0,
        "rho_kg_per_m3": 2700.0,
        "delta_t_k": 35.0,
        "min_spacing_m": 0.0015,
        "margin_spacing_m": None,
        "mass_cap_kg": 0.45,
    },
)


def verify_child(child, env=None):
    """Check one child against the documented feasibility constraints.

    child may be a genome or {"genome": ...}. Returns every violated
    constraint by name (min_spacing_m / mass_cap_kg) with the actual
    value and the limit. A valid child has an empty violations list.
    """
    genome = (child.get("genome", child) if isinstance(child, dict)
              else child)
    genome = model.parse_genome(genome)
    env = env or model.TRAIN_ENV
    geo = model.geometry(genome, env)
    violations = []
    if not geo["spacing_ok"]:
        violations.append({
            "constraint": "min_spacing_m",
            "actual": geo["spacing_m"],
            "limit": env["min_spacing_m"],
        })
    if not geo["mass_ok"]:
        violations.append({
            "constraint": "mass_cap_kg",
            "actual": geo["mass_kg"],
            "limit": env["mass_cap_kg"],
        })
    return {
        "passed": not violations,
        "violations": violations,
        "violation_names": [v["constraint"] for v in violations],
        "genome": list(genome),
        "env": env["name"],
    }


def verify_champion(genome, reference=model.REFERENCE_GENOME,
                    held_out_envs=HELD_OUT_ENVS):
    """Re-score a candidate genome under the held-out envs.

    Returns a verdict dict: {passed, champion_status, checks},
    where each check carries the environment name, both designs'
    raw heat, both feasibility results, and whether the
    candidate beat the reference by the margin there. The
    verdict is a record, not a vibe: run_demo.py files it into
    the run log verbatim.
    """
    checks = []
    passed = True
    for env in held_out_envs:
        geo = model.geometry(genome, env)
        feasible = geo["spacing_ok"] and geo["mass_ok"]
        champ_q = model.heat_watts(genome, env)
        ref_q = model.heat_watts(reference, env)
        beat = champ_q >= BEAT_MARGIN * ref_q
        ok = feasible and beat
        passed = passed and ok
        checks.append({
            "env": env["name"],
            "feasible": feasible,
            "spacing_ok": geo["spacing_ok"],
            "mass_ok": geo["mass_ok"],
            "champion_heat_w": champ_q,
            "reference_heat_w": ref_q,
            "beat_reference": beat,
            "passed": ok,
        })
    return {
        "passed": passed,
        "champion_status": "verified-candidate" if passed else "rejected",
        "beat_margin": BEAT_MARGIN,
        "reference_genome": list(reference),
        "checks": checks,
    }
