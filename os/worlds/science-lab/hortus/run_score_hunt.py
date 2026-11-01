"""Score hunt: four single-lever experiments on the rung-2
calibrated Hortus scorer (boss's order, 2026-11-01: "find
something that will make the score go up").

Baseline (hortus-calibrated-run.jsonl, organism 8175):
seed 20261101, 300 generations, population 48, shipped
GENE_BOUNDS, calibrated natural-convection train env,
calibrated held-out gate. Final best 53.1321. Its best-score
curve FLATTENED: the champion was born at generation 177 and
the score did not improve at all after generation ~200.

Every hunt experiment shares a fresh seed (20261102) so the
levers are compared on equal RNG footing, and each changes
exactly ONE lever against the baseline protocol. Scores are
comparable only where the lever is a DESIGN lever: experiments
C and D change the scoring CONDITIONS (airflow regime,
material), so their raw scores live in different environments
and are labelled CONDITION results everywhere they are filed.

A  LONGER SEARCH (design lever). Same bounds, same calibrated
   env and gate; 3,000 generations instead of 300.
B  WIDER GENOME (design lever). Fin count max 40 -> 60, fin
   height max 60 -> 100 mm, base thickness range 1.0-8.0 ->
   1.0-3.0 mm. Fin thickness bounds UNCHANGED (0.4-4.0 mm):
   the ordered lower bound (0.40 mm) already equals the
   shipped one. 1,500 generations, population 64. The rung-2
   champion sat exactly on the fin-count and fin-height
   maxima, so this tests whether it was pinned by the walls.
C  FORCED AIR (condition lever). Same bounds as A; train env
   h replaced by 28.0 * CALIBRATED_H_MULTIPLIER = 9.9445
   W/m2K (h = 28 is the nominal forced-air coefficient the
   verifier's own held-out set already uses, scaled once by
   the calibration multiplier). EXTRAPOLATED: the multiplier
   was fitted on natural-convection datasheets only; the code
   has a single h and does not separate convection regimes,
   so no component-wise application is possible. The gate is
   the unchanged calibrated held-out set.
D  COPPER (condition lever). Same bounds and protocol as A;
   train env k 237 -> 398 W/mK and rho 2700 -> 8960 kg/m3
   (copper: k = 398 W/mK, pure copper at 25 C, CRC Handbook
   value as tabulated by MatWeb; rho = 8,960 kg/m3, the
   standard density of pure copper). The mass cap and mass
   penalty see the real copper density - copper does not get
   to cheat the mass term. The verifier gate mirrors the
   material (k and rho set to copper in all three calibrated
   held-out envs, names suffixed -copper) so mass feasibility
   is judged at copper density; every other gate parameter is
   unchanged and the reference is re-scored in the same envs.

Each run writes a NEW JSONL log (refuses to overwrite) and a
small summary JSON beside it. The comparison table and the
overall best champion filing are produced from these summaries
(records/SCORE_HUNT.md).

Usage: python3 -m hortus.run_score_hunt [A|B|C|D|all]
"""

import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine  # noqa: E402
    import model  # noqa: E402
    import records as records_mod  # noqa: E402
else:
    from . import engine, model
    from . import records as records_mod

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS_DIR = os.path.join(HERE, "records")
SEED = 20261102
BASE_LABEL = "hortus-toy-fin-v1+calh-%s" % model.CALIBRATED_H_MULTIPLIER

# Experiment B bounds: (n_fins, fin height mm, fin thickness mm,
# base thickness mm). Changes vs model.GENE_BOUNDS are listed in
# the module docstring and in records/SCORE_HUNT.md.
WIDE_BOUNDS = (
    (2.0, 60.0),
    (4.0, 100.0),
    (0.4, 4.0),
    (1.0, 3.0),
)

COPPER_K_W_PER_MK = 398.0
COPPER_RHO_KG_PER_M3 = 8960.0


def _forced_air_env():
    env = model.calibrated_train_env()
    env["name"] = "train-forced-air-calibrated-extrapolated"
    env["h_w_per_m2k"] = 28.0 * model.CALIBRATED_H_MULTIPLIER
    return env


def _copper_env():
    env = model.calibrated_train_env()
    env["name"] = "train-nominal-calibrated-copper"
    env["k_w_per_mk"] = COPPER_K_W_PER_MK
    env["rho_kg_per_m3"] = COPPER_RHO_KG_PER_M3
    return env


def _copper_held_out_envs():
    envs = []
    for env in model.calibrated_held_out_envs():
        mirrored = dict(env)
        mirrored["name"] = env["name"] + "-copper"
        mirrored["k_w_per_mk"] = COPPER_K_W_PER_MK
        mirrored["rho_kg_per_m3"] = COPPER_RHO_KG_PER_M3
        envs.append(mirrored)
    return tuple(envs)


EXPERIMENTS = {
    "A": {
        "title": "longer search (design lever)",
        "log": "hortus-hunt-a-long-run.jsonl",
        "generations": 3000,
        "population_size": 48,
        "env": model.calibrated_train_env,
        "held_out_envs": model.calibrated_held_out_envs,
        "gene_bounds": None,
    },
    "B": {
        "title": "wider genome (design lever)",
        "log": "hortus-hunt-b-wide-run.jsonl",
        "generations": 1500,
        "population_size": 64,
        "env": model.calibrated_train_env,
        "held_out_envs": model.calibrated_held_out_envs,
        "gene_bounds": WIDE_BOUNDS,
    },
    "C": {
        "title": "forced air (condition lever, EXTRAPOLATED)",
        "log": "hortus-hunt-c-forced-run.jsonl",
        "generations": 1500,
        "population_size": 48,
        "env": _forced_air_env,
        "held_out_envs": model.calibrated_held_out_envs,
        "gene_bounds": None,
    },
    "D": {
        "title": "copper (condition lever)",
        "log": "hortus-hunt-d-copper-run.jsonl",
        "generations": 1500,
        "population_size": 48,
        "env": _copper_env,
        "held_out_envs": _copper_held_out_envs,
        "gene_bounds": None,
    },
}


def _curve_facts(path):
    """Best-score curve facts from a finished run log: the last
    generation whose best improved on everything before it, and
    the best score at selected generations."""
    recs = records_mod.load_records(path)
    gens = [r for r in recs if r["kind"] == "generation"]
    bests = {g["generation"]: g["best_score"] for g in gens}
    last_improvement = 0
    running = None
    for gen in sorted(bests):
        if running is None or bests[gen] > running + 1e-12:
            if running is not None:
                last_improvement = gen
            running = bests[gen]
    checkpoints = {}
    for gen in (300, 1000, 1500, 3000):
        if gen in bests:
            checkpoints[str(gen)] = bests[gen]
    return {
        "generations_recorded": len(gens),
        "last_improvement_generation": last_improvement,
        "best_at_generation": checkpoints,
    }


def run_one(key):
    spec = EXPERIMENTS[key]
    log_path = os.path.join(RECORDS_DIR, spec["log"])
    summary_path = os.path.join(
        RECORDS_DIR, "score-hunt-%s.summary.json" % key.lower())
    for path in (log_path, summary_path):
        if os.path.exists(path):
            print("refusing to overwrite: %s" % path)
            return None
    summary = engine.run_evolution(
        log_path,
        seed=SEED,
        generations=spec["generations"],
        population_size=spec["population_size"],
        env=spec["env"](),
        held_out_envs=spec["held_out_envs"](),
        gene_bounds=spec["gene_bounds"],
        model_label=BASE_LABEL + "+hunt" + key)
    verdict = summary["verdict"]
    out = {
        "experiment": key,
        "title": spec["title"],
        "seed": SEED,
        "generations": spec["generations"],
        "population_size": spec["population_size"],
        "gene_bounds": [list(b) for b in (
            spec["gene_bounds"] or model.GENE_BOUNDS)],
        "train_env": spec["env"](),
        "run_log": spec["log"],
        "first_best_score": summary["first_best_score"],
        "final_best_score": summary["final_best_score"],
        "final_mean_score": summary["final_mean_score"],
        "champion_id": summary["champion_id"],
        "champion_genome": [round(g, 6)
                             for g in summary["champion_genome"]],
        "verifier": {
            "passed": verdict["passed"],
            "champion_status": verdict["champion_status"],
            "checks": verdict["checks"],
        },
        "curve": _curve_facts(log_path),
    }
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print("experiment %s (%s)" % (key, spec["title"]))
    print("  log:        %s" % log_path)
    print("  first best: %.4f -> final best: %.4f (mean %.4f)"
          % (out["first_best_score"], out["final_best_score"],
             out["final_mean_score"]))
    print("  champion:   organism %d, genome %s"
          % (out["champion_id"], tuple(out["champion_genome"])))
    print("  verifier:   %s (%s)"
          % ("PASSED" if verdict["passed"] else "REJECTED",
             verdict["champion_status"]))
    print("  curve:      last improvement at generation %d of %d"
          % (out["curve"]["last_improvement_generation"],
             out["generations"]))
    return out


def main(argv):
    keys = ["A", "B", "C", "D"] if len(argv) < 2 or argv[1] == "all" \
        else [argv[1].upper()]
    for key in keys:
        if key not in EXPERIMENTS:
            print("unknown experiment: %s" % key)
            return 1
        if run_one(key) is None:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
