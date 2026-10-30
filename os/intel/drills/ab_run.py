"""intel/drills/ab_run.py -- OS-106 drill (Milo).

Acceptance: one A/B result in hand for the demo's
one comparison (bare launch vs mind image): the
same jobs, both versions, times and acceptance
outcomes recorded; at least one observed stall
correctly attributed as an image defect, with the
journal evidence named.

What fixtures can prove, and what they cannot,
stated plainly. The module (intel/abrun.py)
records a fixture comparison and attributes
fixture stalls; it never runs a live agent, never
touches a process, and never posts to the bus.
The OS-105 A/B eval harness (Buffy) has not
landed, so this drill runs the comparison in the
OS-105 shape on fixtures instead of executing
that harness: a fixed suite, two fixture image
versions, time and outcome per job per version.
No booted test image runs in this repo, so a
live A/B result on a booted image is not claimed
here, and the board view of the result (Rowan
OS-107) is not part of this drill.

Phases, all on fixtures with a fake clock (base
time T0 is irrelevant here; seconds are recorded
per job run, not wall time):

- comparison-table: four jobs under bare and
  under mind-v1. Same job ids both versions, every
  row carrying seconds and an outcome, mind-v1
  faster in total and passing more jobs.
- missing-skill defect: bare job-a stalls needing
  skill git-review, which the bare launch does
  not carry. Attribution is image-defect
  missing-skill, and the evidence names the skill.
- thin-brief defect: bare job-b stalls for want
  of repo context under a thin brief. Attribution
  is image-defect thin-brief.
- bad-instruction attribution: a fixture image
  carrying the instruction "skip acceptance
  checks" yields a bad-instruction defect when a
  stall names it, while a stall naming an
  instruction the image does not carry yields no
  defect. The layer must actually carry the fault.
- worker-failure control: job-c's worker dies
  mid-job under both versions. Both attributions
  are worker-failure, and job-c contributes zero
  defects, so a dead worker is never blamed on the
  image. A stall naming a skill the image does
  carry is likewise no defect.
- malformed-and-immutable: malformed versions,
  runs, and stalls yield no crash and no invented
  result; the revision note proposes a skill add
  for git-review and a thicker brief, and nothing
  auto-applies; inputs are unchanged; the module
  imports no banned module.
"""

import ast
import copy
import os
import sys

sys.path.insert(0, ".")

from intel import abrun  # noqa: E402

BARE = {"name": "bare", "version": "bare",
        "skills": [], "instructions": [], "brief": "thin"}
MIND = {"name": "mind", "version": "mind-v1",
        "skills": ["git-review", "brief-read"],
        "instructions": ["verify acceptance before closing"],
        "brief": "full"}

JOBS = ["job-a", "job-b", "job-c", "job-d"]

RUNS = {
    "bare": {
        "job-a": {"job": "job-a", "seconds": 420, "outcome": "fail",
                  "stalls": [{"job": "job-a",
                              "reason": "stalled waiting for a skill",
                              "journal": ["worker stalled: needs skill "
                                          "git-review to review the patch"],
                              "missing_skill": "git-review"}]},
        "job-b": {"job": "job-b", "seconds": 300, "outcome": "fail",
                  "stalls": [{"job": "job-b",
                              "reason": "stalled for context",
                              "journal": ["worker stalled: no repo "
                                          "context in the brief"],
                              "thin_brief": True}]},
        "job-c": {"job": "job-c", "seconds": 200, "outcome": "fail",
                  "stalls": [{"job": "job-c",
                              "reason": "worker died",
                              "journal": ["worker process died mid-job"],
                              "worker_cause": "worker died"}]},
        "job-d": {"job": "job-d", "seconds": 180, "outcome": "pass",
                  "stalls": []},
    },
    "mind-v1": {
        "job-a": {"job": "job-a", "seconds": 120, "outcome": "pass",
                  "stalls": []},
        "job-b": {"job": "job-b", "seconds": 90, "outcome": "pass",
                  "stalls": []},
        "job-c": {"job": "job-c", "seconds": 200, "outcome": "fail",
                  "stalls": [{"job": "job-c",
                              "reason": "worker died",
                              "journal": ["worker process died mid-job"],
                              "worker_cause": "worker died"}]},
        "job-d": {"job": "job-d", "seconds": 60, "outcome": "pass",
                  "stalls": []},
    },
}

IMAGES = {"bare": BARE, "mind-v1": MIND}


def check(name, ok, detail=""):
    """One phase verdict, printed, returned as a bool."""
    print("%s: %s%s" % (name, "PASS" if ok else "FAIL",
                        (" (" + detail + ")") if detail and not ok else ""))
    return ok


def phase_comparison_table():
    """Same jobs, both versions, times and outcomes recorded."""
    result = abrun.run_comparison(JOBS, RUNS, IMAGES)
    if result["jobs"] != JOBS:
        return check("comparison-table", False, "job list changed")
    if result["versions"] != ["bare", "mind-v1"]:
        return check("comparison-table", False, "version list changed")
    for row in result["table"]:
        for version in ("bare", "mind-v1"):
            entry = row["versions"][version]
            if entry["seconds"] is None or entry["outcome"] == "missing":
                return check("comparison-table", False,
                             "row %s %s unrecorded" % (row["job"], version))
    totals = result["totals"]
    if totals["bare"]["seconds"] != 1100:
        return check("comparison-table", False, "bare total not 1100")
    if totals["mind-v1"]["seconds"] != 470:
        return check("comparison-table", False, "mind total not 470")
    if totals["mind-v1"]["passed"] != 3 or totals["bare"]["passed"] != 1:
        return check("comparison-table", False, "pass counts wrong")
    lines = abrun.measurement_records(result)
    if len(lines) != 8:
        return check("comparison-table", False, "not 8 measurements")
    return check("comparison-table", True)


def phase_missing_skill():
    """Bare job-a stall is a missing-skill image defect."""
    result = abrun.run_comparison(JOBS, RUNS, IMAGES)
    defects = [d for d in result["defects"]
               if d["job"] == "job-a" and d["version"] == "bare"]
    if len(defects) != 1:
        return check("missing-skill", False, "job-a defect count wrong")
    defect = defects[0]
    if defect["kind"] != "missing-skill":
        return check("missing-skill", False, "kind not missing-skill")
    if not any("git-review" in line for line in defect["evidence"]):
        return check("missing-skill", False, "evidence lacks the skill")
    if any(d["job"] == "job-a" and d["version"] == "mind-v1"
           for d in result["defects"]):
        return check("missing-skill", False, "mind-v1 blamed too")
    return check("missing-skill", True)


def phase_thin_brief():
    """Bare job-b stall is a thin-brief image defect."""
    result = abrun.run_comparison(JOBS, RUNS, IMAGES)
    defects = [d for d in result["defects"]
               if d["job"] == "job-b" and d["version"] == "bare"]
    if len(defects) != 1 or defects[0]["kind"] != "thin-brief":
        return check("thin-brief", False, "job-b defect not thin-brief")
    if not any("repo context" in line for line in defects[0]["evidence"]):
        return check("thin-brief", False, "evidence lacks the context line")
    return check("thin-brief", True)


def phase_bad_instruction():
    """A carried bad instruction is a defect; an uncarried one is not."""
    bad_image = {"name": "mind", "version": "mind-v0",
                 "skills": ["git-review"],
                 "instructions": ["skip acceptance checks"],
                 "brief": "full"}
    stall = {"job": "job-x", "reason": "acceptance skipped",
             "journal": ["worker followed instruction skip acceptance "
                         "checks and closed early"],
             "bad_instruction": "skip acceptance checks"}
    kind, detail, evidence = abrun.attribute_stall(stall, bad_image)
    if (kind, detail) != ("image-defect", "bad-instruction"):
        return check("bad-instruction", False, "carried fault not a defect")
    if not any("skip acceptance checks" in line for line in evidence):
        return check("bad-instruction", False, "evidence lacks instruction")
    stranger = dict(stall)
    stranger["bad_instruction"] = "never in this image"
    kind, detail, _ = abrun.attribute_stall(stranger, bad_image)
    if kind == "image-defect":
        return check("bad-instruction", False, "uncarried fault blamed")
    return check("bad-instruction", True)


def phase_worker_failure():
    """A dead worker is a worker failure under both versions."""
    result = abrun.run_comparison(JOBS, RUNS, IMAGES)
    if any(d["job"] == "job-c" for d in result["defects"]):
        return check("worker-failure", False, "job-c blamed on an image")
    for version in ("bare", "mind-v1"):
        stall = RUNS[version]["job-c"]["stalls"][0]
        kind, detail, _ = abrun.attribute_stall(stall, IMAGES[version])
        if (kind, detail) != ("worker-failure", "worker died"):
            return check("worker-failure", False,
                         "job-c %s not worker-failure" % version)
    carried = {"job": "job-y", "reason": "stalled",
               "journal": ["worker stalled: needs skill git-review"],
               "missing_skill": "git-review"}
    kind, _, _ = abrun.attribute_stall(carried, MIND)
    if kind == "image-defect":
        return check("worker-failure", False, "carried skill blamed")
    return check("worker-failure", True)


def phase_malformed_and_immutable():
    """Malformed input is safe; revision note proposes, never applies."""
    jobs_before = copy.deepcopy(JOBS)
    runs_before = copy.deepcopy(RUNS)
    result = abrun.run_comparison(None, None, None)
    if result["jobs"] != [] or result["defects"] != []:
        return check("malformed-and-immutable", False,
                     "malformed input invented a result")
    result = abrun.run_comparison(JOBS, RUNS, IMAGES)
    note = abrun.revision_note(result["defects"])
    changes = note["next_version_changes"]
    if not any("git-review" in change for change in changes):
        return check("malformed-and-immutable", False,
                     "note lacks the skill add")
    if not any("brief" in change for change in changes):
        return check("malformed-and-immutable", False,
                     "note lacks the brief change")
    if "auto" in note["note"] and "nothing auto-applies" not in note["note"]:
        return check("malformed-and-immutable", False, "note claims applying")
    if JOBS != jobs_before or RUNS != runs_before:
        return check("malformed-and-immutable", False, "inputs mutated")
    module_path = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "abrun.py"))
    with open(module_path) as handle:
        tree = ast.parse(handle.read())
    banned = {"socket", "urllib", "requests", "redis", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
            if names & banned:
                return check("malformed-and-immutable", False,
                             "module imports a banned module")
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in banned:
                return check("malformed-and-immutable", False,
                             "module imports a banned module")
    return check("malformed-and-immutable", True)


def main():
    """Run all phases; exit 0 only when every phase passes."""
    phases = [phase_comparison_table,
              phase_missing_skill,
              phase_thin_brief,
              phase_bad_instruction,
              phase_worker_failure,
              phase_malformed_and_immutable]
    results = [phase() for phase in phases]
    print("%d/%d phases PASS" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
