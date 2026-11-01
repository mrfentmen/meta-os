"""Re-run the Hortus demo under the rung-2 calibrated scorer.

Same protocol as run_demo.py (300 generations, population 48,
seed 20261101) so the two runs differ ONLY in the scorer's
coefficient: the training environment and the verifier's three
held-out environments are the calibrated ones from model.py
(h scaled once by model.CALIBRATED_H_MULTIPLIER, fitted against
real datasheet parts - see calibration/CALIBRATION.md).

Writes a NEW run log (refuses to overwrite, like run_demo.py)
and re-files the champion as a JSON record next to it whose
level text states the rung honestly: rung 2 of 4, with the
calibration's held-out validation error, and what rung 2 is
not (not simulation-verified, not fabricated or measured).

Usage: python3 -m hortus.run_calibrated [records_path]
"""

import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine  # noqa: E402
    import model  # noqa: E402
else:
    from . import engine, model

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RECORDS = os.path.join(
    HERE, "records", "hortus-calibrated-run.jsonl")
FILING_PATH = os.path.join(
    HERE, "records", "hortus-calibrated-champion.json")
RESULTS_PATH = os.path.join(
    HERE, "calibration", "results.json")

MODEL_LABEL = "hortus-toy-fin-v1+calh-%s" % model.CALIBRATED_H_MULTIPLIER


def level_text(validation):
    """The champion's re-filed level text. Built from the
    calibration results file so the stated error is the
    measured one, never a hand-typed approximation."""
    return (
        "champion under calibrated scorer (validation error "
        "+-%.1f%% RMS, %.1f%% mean absolute, on %d held-out "
        "datasheet parts never used in fitting) - rung 2 of 4; "
        "not simulation-verified, not fabricated/measured"
        % (validation["rms_pct"], validation["mean_abs_pct"],
           validation["count"]))


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_RECORDS
    if os.path.exists(path):
        print("refusing to overwrite existing run log: %s" % path)
        return 1
    if os.path.exists(FILING_PATH):
        print("refusing to overwrite champion filing: %s" % FILING_PATH)
        return 1
    with open(RESULTS_PATH, "r", encoding="utf-8") as fh:
        results = json.load(fh)
    validation = results["subsets"]["validation"]["after"]

    summary = engine.run_evolution(
        path,
        env=model.calibrated_train_env(),
        held_out_envs=model.calibrated_held_out_envs(),
        model_label=MODEL_LABEL)

    verdict = summary["verdict"]
    filing = {
        "champion_id": summary["champion_id"],
        "champion_genome": [round(g, 6)
                             for g in summary["champion_genome"]],
        "run_log": os.path.basename(path),
        "model": MODEL_LABEL,
        "scorer_calibration": {
            "h_multiplier": model.CALIBRATED_H_MULTIPLIER,
            "fitted_on": model.CALIBRATION_PROVENANCE["fitted_on"],
            "report": model.CALIBRATION_PROVENANCE["report"],
        },
        "first_best_score": summary["first_best_score"],
        "final_best_score": summary["final_best_score"],
        "verifier": {
            "passed": verdict["passed"],
            "champion_status": verdict["champion_status"],
            "checks": verdict["checks"],
        },
        "evidence_level_cap": engine.EVIDENCE_LEVEL_CAP,
        "is_prediction": True,
        "level_text": level_text(validation),
    }
    with open(FILING_PATH, "w", encoding="utf-8") as fh:
        json.dump(filing, fh, indent=1, sort_keys=True)

    print("records:        %s" % path)
    print("generations:    %d (population %d, seed %d)"
          % (summary["generations"], summary["population_size"],
             summary["seed"]))
    print("first best:     %.4f W-equivalent score"
          % summary["first_best_score"])
    print("final best:     %.4f" % summary["final_best_score"])
    print("final mean:     %.4f" % summary["final_mean_score"])
    print("champion:       organism %d, genome %s"
          % (summary["champion_id"],
             tuple(round(g, 3) for g in summary["champion_genome"])))
    print("verifier:       %s (%s)"
          % ("PASSED" if verdict["passed"] else "REJECTED",
             verdict["champion_status"]))
    for check in verdict["checks"]:
        print("  %-28s feasible=%s champion=%.2fW reference=%.2fW "
              "beat=%s" % (check["env"], check["feasible"],
                           check["champion_heat_w"],
                           check["reference_heat_w"],
                           check["beat_reference"]))
    print("filing:         %s" % FILING_PATH)
    print("level:          %s" % filing["level_text"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
