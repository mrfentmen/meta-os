"""Run the shipped Hortus demo: one real evolution, fully recorded.

Usage: python3 -m hortus.run_demo [records_path]

Executes a complete run (default 300 generations, population 48,
seed 20261101) against the toy fin model in model.py, verifies
the champion through the held-out gate, and writes the entire
history — every birth, death, generation summary, and the
verdict — to a JSONL file under hortus/records/.

The demo refuses to overwrite an existing records file: a run
log is evidence, and silently replacing it would be exactly the
record-keeping failure this pack exists to prevent. Pass a new
path for a new run.

Prints a plain summary. The numbers in it are the run's actual
numbers, read back from what the engine produced.
"""

import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine  # noqa: E402
else:
    from . import engine

DEFAULT_RECORDS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "records", "hortus-demo-run.jsonl")


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_RECORDS
    if os.path.exists(path):
        print("refusing to overwrite existing run log: %s" % path)
        return 1
    summary = engine.run_evolution(path)
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
    verdict = summary["verdict"]
    print("verifier:       %s (%s)"
          % ("PASSED" if verdict["passed"] else "REJECTED",
             verdict["champion_status"]))
    for check in verdict["checks"]:
        print("  %-22s feasible=%s champion=%.2fW reference=%.2fW "
              "beat=%s" % (check["env"], check["feasible"],
                           check["champion_heat_w"],
                           check["reference_heat_w"],
                           check["beat_reference"]))
    print("evidence cap:   ladder level %d — candidate only, "
          "not a discovery claim" % engine.EVIDENCE_LEVEL_CAP)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
