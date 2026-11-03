#!/usr/bin/env python3
"""Design-job loop for META OFFICINA (stage 1).

The workshop loop, on the repo's job-board pattern (post, claim,
complete or fail with a reason — the same state machine os/jobs.py
runs on the bus, here kept offline so the loop and its tests need
no Redis and no network):

  1. Post one job per sampled variant.
  2. Claim each job, score it with the heatsink simulator, and
     complete it (feasible) or fail it (constraint violation, with
     the score still recorded).
  3. Keep winners: the feasible jobs with the lowest thermal
     resistance. Record every failure with its score.
  4. Acceptance gate: the best design only counts as
     'workshop-proven' after an independent re-score under
     held-out conditions (different airflow plus a fixed
     manufacturing-tolerance perturbation of the geometry). The
     re-score recomputes from the parameters — it never trusts a
     stored score — and the design must clear the stage-1 bar
     (R <= 2.0 degC/W) at design conditions AND held out, and
     stay feasible held out.

Stage-1 bar, stated plainly: 2.0 degC/W is a chosen workshop
threshold for this 50x50 mm aluminium sink (it clears 55 K at
27.5 W and up). It is not a law of physics; a later stage may
move it, and the run record names it so the number stays honest.

No model calls anywhere. The simulator is code; the loop only
counts what the simulator returns.
"""

import json
import math
import random
import threading

from heatsink import (
    BASE_THICKNESS_MM,
    FIN_COUNT,
    FIN_HEIGHT_MM,
    FIN_THICKNESS_MM,
    Conditions,
    HeatsinkParams,
    simulate,
)

# Stage-1 acceptance bar (degC/W), at design conditions and held out.
ACCEPT_R_C_PER_W = 2.0
# Held-out conditions: forced airflow the design run never saw.
HELDOUT_CONDITIONS = Conditions(h_w_m2k=15.0, t_base_c=80.0, t_amb_c=25.0)
# Fixed manufacturing-tolerance perturbation for the held-out re-score.
HELDOUT_TOLERANCE_T = 1.05  # fin 5% thicker than drawn
HELDOUT_TOLERANCE_H = 0.98  # fin 2% shorter than drawn
# Claimed-score agreement for the re-score (fresh computation must
# match the claimed number this tightly, or the claim is rejected).
CLAIM_TOLERANCE = 1e-6


class DesignJob:
    """One design variant moving through post -> claim -> done/failed."""

    def __init__(self, job_id, params):
        self.job_id = job_id
        self.params = params
        self.status = "posted"
        self.score = None
        self.failure_reason = None

    def as_dict(self):
        return {
            "job_id": self.job_id,
            "params": self.params.as_dict(),
            "status": self.status,
            "score_r_th_c_per_w": self.score,
            "failure_reason": self.failure_reason,
        }


class DesignBoard:
    """In-memory job board with an atomic claim (one worker wins)."""

    def __init__(self):
        self._jobs = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def post(self, params):
        with self._lock:
            job = DesignJob(self._next_id, params)
            self._jobs[self._next_id] = job
            self._next_id += 1
            return job

    def claim(self):
        """Claim the oldest posted job, or None when none is posted."""
        with self._lock:
            for job in sorted(self._jobs.values(), key=lambda j: j.job_id):
                if job.status == "posted":
                    job.status = "claimed"
                    return job
        return None

    def complete(self, job, score):
        with self._lock:
            job.status = "done"
            job.score = score

    def fail(self, job, score, reason):
        with self._lock:
            job.status = "failed"
            job.score = score
            job.failure_reason = reason

    def all_jobs(self):
        return sorted(self._jobs.values(), key=lambda j: j.job_id)


def sample_variant(rng):
    """Draw one variant inside the declared ranges (seeded: the same
    seed always draws the same variants, so a run replays exactly)."""
    return HeatsinkParams(
        fin_height_mm=rng.uniform(*FIN_HEIGHT_MM),
        fin_thickness_mm=rng.uniform(*FIN_THICKNESS_MM),
        fin_count=rng.randint(*FIN_COUNT),
        base_thickness_mm=rng.uniform(*BASE_THICKNESS_MM),
    )


def stop_requested(stop_path):
    """True when the operator's STOP file exists.

    A missing path is not a stop: the loop reads the file, it never assumes one.
    Kept as a function so a test can call it without starting a service.
    """
    if not stop_path:
        return False
    import os
    return os.path.exists(stop_path)


def run_loop(n_variants, seed, conditions=None, top_k=5, stop_path=None):
    """Run one design loop. Returns a run record dict (JSON-ready):
    every job with its score, every failure with its reason, the
    best-so-far feasible score curve, and the top-k winners.

    `stop_path`, when given, is checked before each claim: if the operator filed
    a STOP file the loop stops where it is, records `stopped: "stop-file"`, and
    reports the jobs it did score. It never deletes the file or clears the stop.
    """
    conditions = conditions or Conditions()
    rng = random.Random(seed)
    board = DesignBoard()
    for _ in range(n_variants):
        board.post(sample_variant(rng))
    curve = []
    best = None
    stopped = None
    while True:
        if stop_requested(stop_path):
            stopped = "stop-file"
            break
        job = board.claim()
        if job is None:
            break
        result = simulate(job.params, conditions)
        if result.feasible:
            board.complete(job, result.r_th_c_per_w)
            if best is None or result.r_th_c_per_w < best:
                best = result.r_th_c_per_w
        else:
            board.fail(
                job, result.r_th_c_per_w, "; ".join(result.violations)
            )
        curve.append(best)
    jobs = board.all_jobs()
    winners = sorted(
        [j for j in jobs if j.status == "done"],
        key=lambda j: j.score,
    )[:top_k]
    failures = [j for j in jobs if j.status == "failed"]
    return {
        "artefact_class": "heatsink-fin-geometry",
        "n_variants": n_variants,
        "seed": seed,
        "conditions": {
            "h_w_m2k": conditions.h_w_m2k,
            "t_base_c": conditions.t_base_c,
            "t_amb_c": conditions.t_amb_c,
        },
        "accept_r_c_per_w": ACCEPT_R_C_PER_W,
        "jobs": [j.as_dict() for j in jobs],
        "failures": [j.as_dict() for j in failures],
        "score_curve_best_so_far": curve,
        "winners": [j.as_dict() for j in winners],
        "best": winners[0].as_dict() if winners else None,
        "stopped": stopped,
    }


def heldout_params(params):
    """The same design as manufactured: thickness up, height down,
    by the fixed tolerance factors. Deterministic, documented."""
    return HeatsinkParams(
        fin_height_mm=params.fin_height_mm * HELDOUT_TOLERANCE_H,
        fin_thickness_mm=params.fin_thickness_mm * HELDOUT_TOLERANCE_T,
        fin_count=params.fin_count,
        base_thickness_mm=params.base_thickness_mm,
    )


def verify_proven(params, claimed_r, design_conditions=None):
    """Independent re-score gate. Recomputes the design-condition
    score from the parameters (never trusts the claimed number),
    then re-scores under held-out conditions and tolerance
    perturbation. Proven only if: the claimed score agrees with
    the fresh computation, the design clears the bar at design
    conditions, and it stays feasible and clears the bar held out.
    Returns a dict with every number, so a pass can be checked.

    design_conditions is the conditions the design was graded
    under (default natural convection). Callers grading under
    other conditions — a forced-airflow brief — must pass them,
    or the gate would re-score under the wrong conditions and
    reject designs that pass where they were graded. The held-out
    re-score always uses HELDOUT_CONDITIONS: for a forced-airflow
    design that is a degraded-airflow check (h=15 against a design
    h=25), stricter than design conditions, which is conservative,
    not a hole."""
    design_conditions = design_conditions or Conditions()
    fresh = simulate(params, design_conditions)
    fresh_ok = (
        fresh.feasible
        and math.isfinite(claimed_r)
        and abs(fresh.r_th_c_per_w - claimed_r)
        <= CLAIM_TOLERANCE * max(1.0, abs(claimed_r))
    )
    held = simulate(heldout_params(params), HELDOUT_CONDITIONS)
    proven = bool(
        fresh_ok
        and fresh.r_th_c_per_w <= ACCEPT_R_C_PER_W
        and held.feasible
        and held.r_th_c_per_w <= ACCEPT_R_C_PER_W
    )
    return {
        "params": params.as_dict(),
        "claimed_r_th_c_per_w": claimed_r,
        "fresh_r_th_c_per_w": fresh.r_th_c_per_w,
        "fresh_agrees": fresh_ok,
        "heldout_r_th_c_per_w": held.r_th_c_per_w,
        "heldout_feasible": held.feasible,
        "heldout_violations": list(held.violations),
        "accept_r_c_per_w": ACCEPT_R_C_PER_W,
        "proven": proven,
    }


def prove_best(record):
    """Gate the run's best design. Returns the verification dict,
    or None when the run produced no feasible winner."""
    best = record.get("best")
    if best is None:
        return None
    params = HeatsinkParams(**best["params"])
    return verify_proven(params, best["score_r_th_c_per_w"])


def select_proven(record):
    """Gate the winners in score order and take the first design
    that proves. A raw winner can fail held out (the overnight
    run's raw best did: its fin gap falls below minimum under
    tolerance), and such a design must NOT be exported as proven.
    Returns {"proven_best", "verification", "attempts"} where
    attempts lists every verification tried, in order."""
    attempts = []
    for winner in record.get("winners", []):
        verification = verify_proven(
            HeatsinkParams(**winner["params"]),
            winner["score_r_th_c_per_w"],
        )
        attempts.append(verification)
        if verification["proven"]:
            return {
                "proven_best": winner,
                "verification": verification,
                "attempts": attempts,
            }
    return {"proven_best": None, "verification": None, "attempts": attempts}


def export_best(record, path):
    """Write the run's best PROVEN design (with its verification)
    as a real file. When no winner proves, the file carries the
    raw best with its failing verification and proven=false, so
    the export never claims more than the gate allowed. Returns
    the path written."""
    selection = select_proven(record)
    if selection["proven_best"] is not None:
        design = selection["proven_best"]
        verification = selection["verification"]
    else:
        design = record["best"]
        verification = prove_best(record)
    payload = {
        "artefact_class": record["artefact_class"],
        "best": design,
        "verification": verification,
        "proven": bool(verification and verification["proven"]),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return path


def main(argv=None):
    """CLI: run one overnight-style loop and record it.
    Usage: design_loop.py <n_variants> <seed> <out_json>"""
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print("usage: design_loop.py <n_variants> <seed> <out_json>")
        return 2
    n_variants, seed, out_path = int(argv[0]), int(argv[1]), argv[2]
    record = run_loop(n_variants, seed, top_k=10)
    selection = select_proven(record)
    record["proven_best"] = selection["proven_best"]
    record["proven_verification"] = selection["verification"]
    record["verification_attempts"] = len(selection["attempts"])
    with open(out_path, "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    best = record["best"]
    proven = selection["proven_best"]
    print(
        "variants=%d failures=%d best_r=%.4f proven_r=%.4f proven=%s -> %s"
        % (
            n_variants,
            len(record["failures"]),
            best["score_r_th_c_per_w"] if best else float("nan"),
            proven["score_r_th_c_per_w"] if proven else float("nan"),
            bool(selection["verification"] and selection["verification"]["proven"]),
            out_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
