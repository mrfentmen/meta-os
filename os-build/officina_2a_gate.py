#!/usr/bin/env python3
"""Officina stage 2a acceptance gate (BUILD WAVE W3, Milo).

Run from the repo root:

    python3 os-build/officina_2a_gate.py

Stage 2a: rough words in, proven design out — the agent turns a
sloppy plain-words description into a structured brief, iterates
the brief itself with no human in the loop (exactly one rule-driven
move per round, every decision logged with its reason and the grade
that motivated it), and nothing counts as proven until the
independent held-out gate passes AND the brief's own target is met.

SIMULATED, stated plainly: every score here comes from the
heatsink simulator in code. Nothing in this gate validates against
a measured physical heatsink, and nothing here runs on a booted
Meta OS image. A PASS means the 2a loop behaves as specified in
code, not that a part is proven in the world.

Exit 0 only if every clause passes. Stdlib only, offline, no model
calls, no network, no bus posts. The only grader is code.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNTIME = os.path.join(ROOT, "os", "worlds", "officina", "runtime")
sys.path.insert(0, RUNTIME)

from brief import (  # noqa: E402
    export_design,
    grading_conditions,
    parse_rough_words,
    run_rough_words,
)
from design_loop import ACCEPT_R_C_PER_W, verify_proven  # noqa: E402
from heatsink import HeatsinkParams  # noqa: E402

# Fresh held-out wording: never one of the recorded runs. The gate
# must pass on words it was not written against, not on a replay.
FRESH_WORDS = (
    "a heatsink for a toasty little board, about 50mm square, "
    "no fan, keep it compact, under 2 degrees per watt"
)
IMPOSSIBLE_WORDS = (
    "a heatsink for a hot chip, about 50mm square, no fan, "
    "under 0.1 degrees per watt"
)

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print("%s %s — %s" % ("PASS" if ok else "FAIL", name, detail))


def main():
    print("OFFICINA 2a ACCEPTANCE GATE (W3) — SIMULATED scores only")
    print("branch: %s" % subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=ROOT).stdout.strip())
    print("tip: %s" % subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, cwd=ROOT).stdout.strip())

    # G1 — intake: only what the words state is recorded as stated.
    brief = parse_rough_words(FRESH_WORDS)
    targets = [t for t in brief["targets"]
               if t["kind"] == "target_r_c_per_w"]
    check("G1-intake-class",
          brief["artefact_class"] == "heatsink-fin-geometry",
          "class=%s" % brief["artefact_class"])
    check("G1-intake-target",
          len(targets) == 1 and targets[0]["value"] == 2.0
          and targets[0]["source"] == "stated",
          "target=%s" % targets)
    check("G1-intake-unknowns",
          any(u["slot"] == "power_w" for u in brief["unknowns"]),
          "unstated power_w in unknowns, not invented")
    check("G1-intake-preferences",
          any(p["kind"] == "compact" for p in brief["preferences"]),
          "ungradeable 'compact' kept as preference, not graded")

    # G2 — self-iteration: no human in the loop, one move per round,
    # every decision logged with reason + motivating grade.
    record = run_rough_words(FRESH_WORDS)
    log = record["brief"]["decision_log"]
    rounds = [e["round"] for e in log]
    check("G2-proven",
          record["status"] == "proven" and record["proven"] is True,
          "status=%s rounds=%d final R=%.4f"
          % (record["status"], record["rounds_used"],
             record["final_grade"]["r_th_c_per_w"]))
    check("G2-log-sequential",
          rounds == list(range(len(log))) and len(set(rounds)) == len(rounds),
          "log rounds %s, exactly one entry per round" % rounds)
    check("G2-log-reasons",
          all(e.get("rule") and e.get("decision") and e.get("reason")
              for e in log)
          and all(e["grade_before"] is not None for e in log[1:]),
          "every entry has rule/decision/reason; every round>=1 "
          "carries its motivating grade")
    check("G2-log-intake-honest",
          log[0]["rule"] == "intake" and log[0]["grade_before"] is None,
          "round 0 is the intake guess, not a graded decision")

    # G3 — held-out independence: re-run the gate from the final
    # parameters and require it to agree with the record.
    final_params = HeatsinkParams(**record["final_params"])
    fresh = verify_proven(
        final_params, record["final_grade"]["r_th_c_per_w"],
        grading_conditions(record["brief"]))
    check("G3-heldout-agrees",
          fresh["proven"] is True
          and fresh["fresh_r_th_c_per_w"]
          == record["verification"]["fresh_r_th_c_per_w"]
          and fresh["heldout_r_th_c_per_w"]
          == record["verification"]["heldout_r_th_c_per_w"],
          "fresh R=%.4f held-out R=%.4f, matches record"
          % (fresh["fresh_r_th_c_per_w"],
             fresh["heldout_r_th_c_per_w"]))
    check("G3-heldout-bar",
          fresh["heldout_feasible"]
          and fresh["heldout_r_th_c_per_w"] <= ACCEPT_R_C_PER_W,
          "held-out feasible, R %.4f <= bar %.1f"
          % (fresh["heldout_r_th_c_per_w"], ACCEPT_R_C_PER_W))

    # G4 — brief's own target: proven requires meeting it, not just
    # the workshop bar.
    check("G4-brief-target",
          record["final_grade"]["r_th_c_per_w"] <= targets[0]["value"],
          "final R %.4f <= stated target %.4f"
          % (record["final_grade"]["r_th_c_per_w"],
             targets[0]["value"]))

    # G5 — negative case + export discipline: an impossible target
    # ends unproven and is never exported as proven.
    bad = run_rough_words(IMPOSSIBLE_WORDS)
    check("G5-impossible-unproven",
          bad["proven"] is False and bad["status"].startswith("unproven"),
          "status=%s rounds=%d, no false proven"
          % (bad["status"], bad["rounds_used"]))
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = export_design(bad, os.path.join(tmp, "bad.json"))
        good_path = export_design(
            record, os.path.join(tmp, "good.json"))
        with open(bad_path) as f:
            bad_out = json.load(f)
        with open(good_path) as f:
            good_out = json.load(f)
    check("G5-export-discipline",
          bad_out["proven"] is False
          and good_out["proven"] is True
          and good_out["verification"]["proven"] is True,
          "unproven exports proven=false; proven exports with "
          "its verification attached")

    # G6 — the existing Officina suite still passes on this branch.
    suite = subprocess.run(
        [sys.executable, "-m", "unittest", "discover",
         "-s", "tests/officina"],
        capture_output=True, text=True, cwd=ROOT)
    tail = (suite.stderr.strip().splitlines() or [""]) [-1]
    check("G6-suite",
          suite.returncode == 0,
          "unittest discover tests/officina rc=%d (%s)"
          % (suite.returncode, tail))

    failed = [n for n, ok, _ in results if not ok]
    print("GATE: %s (%d/%d clauses)"
          % ("PASS" if not failed else "FAIL", len(results) - len(failed),
             len(results)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
