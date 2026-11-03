"""Hortus run-003 driver (OC2B-308-309). Stdlib only.

Reads no inputs besides the fixed params below. Writes in its own
directory: records.jsonl (full engine log), generations.csv (gens 1-8,
best+mean), winner.json (champion genome + sha256), fitness.svg
(best+mean curve, hand-rolled SVG so no matplotlib is needed).

Deterministic: engine.run_evolution is driven by one random.Random(seed).
Usage: python3 run.py   (run from this directory)
"""
import csv
import hashlib
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.normpath(os.path.join(
    _HERE, "..", "..", "..", "..", "os", "worlds", "science-lab"))
if not os.path.isdir(os.path.join(_LAB, "hortus")):
    # Clean-directory re-run: engine located via REPO_ROOT env.
    _LAB = os.path.join(os.environ.get("REPO_ROOT", _LAB), "os", "worlds",
                        "science-lab")
sys.path.insert(0, _LAB)

from hortus import engine, model, records as records_mod  # noqa: E402

RUN_ID = "run-003"
SEED = 500001
POPULATION_SIZE = 20
GENERATIONS = 8
USE_CALIBRATED = True  # run-003: calibrated fitness (OC2B-307)


def svg_curve(rows, path):
    """Two-series line chart (best, mean) as deterministic SVG."""
    w, h, pad = 560, 320, 48
    vals = [r[1] for r in rows] + [r[2] for r in rows]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    lo -= 0.05 * span
    hi += 0.05 * span

    def x(i):
        return pad + (w - 2 * pad) * (i / max(len(rows) - 1, 1))

    def y(v):
        return h - pad - (h - 2 * pad) * ((v - lo) / (hi - lo))

    def poly(col, idx):
        pts = " ".join("%.1f,%.1f" % (x(i), y(r[idx]))
                       for i, r in enumerate(rows))
        return ('<polyline points="%s" fill="none" stroke="%s" '
                'stroke-width="2"/>' % (pts, col))

    dots = []
    for i, r in enumerate(rows):
        dots.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#1f6feb"/>'
                    % (x(i), y(r[1])))
        dots.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#cf222e"/>'
                    % (x(i), y(r[2])))
    grid = []
    for f in (0.0, 0.5, 1.0):
        gy = pad + (h - 2 * pad) * f
        gv = hi - (hi - lo) * f
        grid.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" '
                    'stroke="#ddd"/>' % (pad, gy, w - pad, gy))
        grid.append('<text x="%d" y="%.1f" font-size="10" '
                    'fill="#555">%.2f</text>' % (4, gy + 3, gv))
    labels = "".join(
        '<text x="%.1f" y="%d" font-size="10" fill="#555">%d</text>'
        % (x(i) - 3, h - pad + 16, r[0]) for i, r in enumerate(rows))
    head = (

        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
        '<rect width="%d" height="%d" fill="white"/>'
        '<text x="%d" y="20" font-size="13" font-family="sans-serif">'
        % (w, h, w, h, pad))
    tail = (

        ' fitness: best (blue) + mean (red) per generation</text>'
        '%s%s%s%s<text x="%d" y="%d" font-size="10" fill="#555">generation'
        '</text></svg>' % ("".join(grid),
                           poly("#1f6feb", 1), poly("#cf222e", 2),
                           "".join(dots) + labels, pad, h - 8))
    svg = head + RUN_ID + tail
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg + "\n")


def main():
    t0 = time.time()
    log_path = os.path.join(_HERE, "records.jsonl")
    if os.path.exists(log_path):
        print("refusing to overwrite existing run log: %s" % log_path)
        return 1
    if USE_CALIBRATED:
        env = model.calibrated_train_env()
        held = model.calibrated_held_out_envs()
        label = "hortus-toy-fin-v1-calibrated"
    else:
        env = dict(model.TRAIN_ENV)
        held = None
        label = None
    summary = engine.run_evolution(
        log_path, seed=SEED, generations=GENERATIONS,
        population_size=POPULATION_SIZE, env=env, held_out_envs=held,
        model_label=label)
    recs = records_mod.load_records(log_path)
    genrecs = [r for r in recs if r.get("kind") == "generation"
               and 1 <= r.get("generation", 0) <= 8]
    rows = [(r["generation"], r["best_score"], r["mean_score"])
            for r in sorted(genrecs, key=lambda r: r["generation"])]
    csv_path = os.path.join(_HERE, "generations.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["generation", "best_score", "mean_score"])
        for g, b, m in rows:
            w.writerow([g, "%.6f" % b, "%.6f" % m])
    genome = [round(float(g), 6) for g in summary["champion_genome"]]
    ghash = hashlib.sha256(
        json.dumps(genome, separators=(",", ":")).encode()).hexdigest()
    with open(os.path.join(_HERE, "winner.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"organism_id": summary["champion_id"], "genome": genome,
                   "genome_sha256": ghash,
                   "final_best_score": summary["final_best_score"],
                   "final_mean_score": summary["final_mean_score"],
                   "verdict": summary["verdict"]}, fh, indent=2,
                  sort_keys=True)
        fh.write("\n")
    svg_curve(rows, os.path.join(_HERE, "fitness.svg"))
    wall = time.time() - t0
    with open(os.path.join(_HERE, "walltime.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("wall_seconds=%.2f\n" % wall)
    print("rows=%d first_best=%.4f final_best=%.4f final_mean=%.4f "
          "champion=%d wall=%.2fs" % (
              len(rows), summary["first_best_score"],
              summary["final_best_score"], summary["final_mean_score"],
              summary["champion_id"], wall))
    return 0


if __name__ == "__main__":
    sys.exit(main())
