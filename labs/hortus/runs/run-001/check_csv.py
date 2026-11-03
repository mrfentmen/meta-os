"""CSV parse check for OC2B-323. Reads all three run generations.csv
files, verifies each parses with rows for generations 1-8 (best+mean
numeric), and prints row counts. Usage: python3 check_csv.py
(run from labs/hortus/runs/run-001/)."""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUNS = os.path.dirname(_HERE)


def check(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    gens = [int(r["generation"]) for r in rows]
    assert gens == [1, 2, 3, 4, 5, 6, 7, 8], "gap: %r" % (gens,)
    for r in rows:
        float(r["best_score"])
        float(r["mean_score"])
    return len(rows)


def main():
    total = 0
    for run in ("run-001", "run-002", "run-003"):
        p = os.path.join(_RUNS, run, "generations.csv")
        n = check(p)
        total += n
        print("%s/generations.csv: OK, %d data rows (generations 1-8)" % (
            run, n))
    print("all three CSVs parse; total data rows: %d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
