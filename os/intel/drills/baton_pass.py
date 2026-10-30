"""Baton pass drill (Milo lane, OS-125).

Acceptance: a worker is killed mid-job; the watchman
passes the baton and the job completes with no repeated
work -- the record shows the deposited progress, zero
duplicated file changes, and a continuation prompt that
names what remains instead of restating the whole job.
In-window the continuation is proven same-program; the
cross-program pass (for example Muse to Freebuff,
possible because both are pre-installed in the image) is
the named stretch line -- run before freeze if the
drivers allow, honestly reported either way.

What fixtures can prove, and what they cannot, stated
plainly. The baton module (intel/baton.py) composes the
continuation from the job record; it never moves a claim.
The overseer moves the claim, and the drill's simulated
overseer move is part of the harness, not a claim about
a live machine. The simulated next worker is in the same
process as the killed worker, so this drill proves the
same-program pass only. A cross-program pass needs two
agent programs and a live overseer move; neither runs
here, so neither is claimed.

Phases, all on fixtures with a fake clock (base time T0):

- full pass: worker pax is killed mid-job 7 after
  depositing progress on a.txt (note plus timestamp) and
  one remaining step. The baton names the goal, the
  deposited note, a.txt as already changed, b.txt and
  c.txt as still to touch, the remaining step, and both
  acceptance checks. The prompt never lists a.txt under
  files still to touch. The simulated next worker hana
  writes only b.txt and c.txt; the written set meets the
  completed set at nothing, so zero file changes are
  duplicated, and the finished record carries all three
  files done.
- no progress: a job with no notes and no completed
  files yields a prompt that says no progress notes were
  deposited and no completed-file record exists, and
  lists every file as still to touch. Nothing is claimed
  done that was not deposited.
- malformed: a non-record, a record without an id, and
  a job id missing from the snapshot all yield no baton
  and no journal record, never a crash. A comma-separated
  files string and a newline-separated accept string parse
  to the same lists as the list forms.
- idempotent and immutable: a second pass tick over the
  same job journals nothing new, and composing leaves
  the job record byte-for-byte unchanged.
- no-dale: the baton record carries no push and no
  announcement field, the baton module imports no push
  module, and the brief line names job, previous worker,
  next worker, and the remaining file count.

What this drill does NOT claim: a live worker actually
killed and resumed, a real overseer claim move on a
booted test image (no test image in this repo), the
watchman's mechanical execution of the pass (Pax
OS-118), or the cross-program pass. Those are the live
and stretch halves; the composition, journal, brief, and
zero-duplication halves are proven here.

Runs unattended on fixtures: no network, no Redis, no
bus posts.

Usage: python3 intel/drills/baton_pass.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import baton  # noqa: E402

T0 = 100000
WORKER = "pax"
NEXT = "hana"


def killed_job():
    return {
        "id": "7",
        "title": "Wire the watchdog status line",
        "goal": "Show one live health line on the boot screen",
        "claim": WORKER,
        "status": "claimed",
        "claimed_at": T0,
        "last_progress_at": T0 + 300,
        "progress_notes": ["wrote a.txt", "tests pass for a.txt"],
        "note": "tests pass for a.txt",
        "files": ["a.txt", "b.txt", "c.txt"],
        "completed_files": ["a.txt"],
        "steps": ["write a.txt", "write b.txt", "write c.txt"],
        "completed_steps": ["write a.txt"],
        "acceptance_checks": ["b.txt renders", "c.txt renders"],
    }


def phase_full_pass():
    job = killed_job()
    snap = {"jobs": [job]}
    composed = baton.compose_baton(job)
    if composed is None:
        print("full-pass: FAIL: no baton composed")
        return False
    if composed["goal"] != job["goal"]:
        print("full-pass: FAIL: baton goal %r is not the job goal"
              % composed["goal"])
        return False
    if composed["progress_notes"] != job["progress_notes"]:
        print("full-pass: FAIL: baton progress %r drops deposited "
              "notes" % composed["progress_notes"])
        return False
    if composed["remaining_files"] != ["b.txt", "c.txt"]:
        print("full-pass: FAIL: remaining files %r, expected "
              "[b.txt, c.txt]" % composed["remaining_files"])
        return False
    if composed["remaining_steps"] != ["write b.txt", "write c.txt"]:
        print("full-pass: FAIL: remaining steps %r"
              % composed["remaining_steps"])
        return False
    prompt = composed["prompt"]
    for needle in ("Show one live health line",
                   "tests pass for a.txt",
                   "write b.txt",
                   "b.txt renders"):
        if needle not in prompt:
            print("full-pass: FAIL: prompt misses %r" % needle)
            return False
    still_section = prompt.split("Files still to touch:")[1]
    still_section = still_section.split("What remains:")[0]
    if "a.txt" in still_section:
        print("full-pass: FAIL: prompt lists completed a.txt as "
              "still to touch")
        return False
    records = baton.baton_pass_tick(snap, "7", NEXT, [], T0 + 600)
    if len(records) != 1 or records[0]["kind"] != "baton-pass":
        print("full-pass: FAIL: pass tick yielded %r" % records)
        return False
    if records[0]["to_worker"] != NEXT:
        print("full-pass: FAIL: pass names %r, expected %s"
              % (records[0]["to_worker"], NEXT))
        return False
    written = set(composed["remaining_files"])
    already = set(composed["completed_files"])
    if written & already:
        print("full-pass: FAIL: next worker repeats %r"
              % sorted(written & already))
        return False
    finished = sorted(written | already)
    if finished != ["a.txt", "b.txt", "c.txt"]:
        print("full-pass: FAIL: finished files %r" % finished)
        return False
    print("full-pass: killed worker %s mid-job 7, baton names "
          "goal, progress, remaining files b/c, remaining steps, "
          "checks; next worker %s writes only b/c, zero duplicated "
          "file changes: PASS" % (WORKER, NEXT))
    return True


def phase_no_progress():
    job = {"id": "8", "title": "Unstarted job", "claim": WORKER,
           "files": ["x.txt", "y.txt"], "accept": "x renders\ny renders"}
    composed = baton.compose_baton(job)
    if composed is None:
        print("no-progress: FAIL: no baton for a job with no "
              "deposited progress")
        return False
    if composed["progress_notes"] != []:
        print("no-progress: FAIL: baton invents progress %r"
              % composed["progress_notes"])
        return False
    if composed["completed_files"] != []:
        print("no-progress: FAIL: baton invents completed files")
        return False
    if composed["remaining_files"] != ["x.txt", "y.txt"]:
        print("no-progress: FAIL: remaining %r"
              % composed["remaining_files"])
        return False
    if "no progress notes deposited" not in composed["prompt"]:
        print("no-progress: FAIL: prompt does not say no progress "
              "was deposited")
        return False
    if composed["acceptance_checks"] != ["x renders", "y renders"]:
        print("no-progress: FAIL: accept string parses to %r"
              % composed["acceptance_checks"])
        return False
    print("no-progress: job with nothing deposited yields an "
          "honest prompt, every file still to touch: PASS")
    return True


def phase_malformed():
    if baton.compose_baton("not a record") is not None:
        print("malformed: FAIL: non-record yields a baton")
        return False
    if baton.compose_baton({"title": "no id"}) is not None:
        print("malformed: FAIL: id-less record yields a baton")
        return False
    if baton.baton_pass_tick({"jobs": []}, "99", NEXT, [],
                             T0) != []:
        print("malformed: FAIL: missing job yields a pass record")
        return False
    if baton.baton_pass_tick({"jobs": []}, "", NEXT, [],
                             T0) != []:
        print("malformed: FAIL: empty job id yields a pass record")
        return False
    string_job = {"id": "9", "title": "String forms",
                  "files": "a.txt, b.txt, a.txt",
                  "completed_files": "a.txt",
                  "accept": "a renders\nb renders\n"}
    composed = baton.compose_baton(string_job)
    if composed is None or composed["files"] != ["a.txt", "b.txt"]:
        print("malformed: FAIL: comma files parse to %r"
              % (composed["files"] if composed else None))
        return False
    if composed["remaining_files"] != ["b.txt"]:
        print("malformed: FAIL: remaining from string forms %r"
              % composed["remaining_files"])
        return False
    spec_job = {"id": "10", "title": "Spec goal",
                "spec": "Goal: Ship the status line\nContext: boot",
                "files": []}
    composed = baton.compose_baton(spec_job)
    if composed is None or composed["goal"] != "Ship the status line":
        print("malformed: FAIL: spec goal reads %r"
              % (composed["goal"] if composed else None))
        return False
    print("malformed: non-records, id-less records, and missing "
          "jobs yield nothing; string and spec forms parse: PASS")
    return True


def phase_idempotent_and_immutable():
    job = killed_job()
    before = copy.deepcopy(job)
    snap = {"jobs": [job]}
    first = baton.baton_pass_tick(snap, "7", NEXT, [], T0 + 600)
    second = baton.baton_pass_tick(snap, "7", NEXT, first, T0 + 700)
    if len(first) != 1 or second != []:
        print("idempotent: FAIL: first tick %d records, second "
              "tick %d records, expected 1 then 0"
              % (len(first), len(second)))
        return False
    if job != before:
        print("immutable: FAIL: composing mutated the job record")
        return False
    lines = baton.baton_brief_lines(first)
    if len(lines) != 1 or "7" not in lines[0] \
            or WORKER not in lines[0] or NEXT not in lines[0] \
            or "2 file(s)" not in lines[0]:
        print("idempotent: FAIL: brief line %r" % lines)
        return False
    print("idempotent: second pass journals nothing, job record "
          "unchanged, brief line names job/workers/count: PASS")
    return True


def phase_no_dale():
    job = killed_job()
    snap = {"jobs": [job]}
    records = baton.baton_pass_tick(snap, "7", NEXT, [], T0 + 600)
    if len(records) != 1:
        print("no-dale: FAIL: pass tick yielded %r" % records)
        return False
    record = records[0]
    if "push" in record or "announcement" in record:
        print("no-dale: FAIL: pass record carries a push or "
              "announcement field")
        return False
    source = open(os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))),
        "baton.py")).read()
    if "intel/push" in source or "import push" in source:
        print("no-dale: FAIL: baton module imports a push path")
        return False
    print("no-dale: pass record is journal only, baton module "
          "has no push path, Dale contacted at no rung: PASS")
    return True


def main():
    phases = [phase_full_pass, phase_no_progress,
              phase_malformed, phase_idempotent_and_immutable,
              phase_no_dale]
    ok = True
    for phase in phases:
        if not phase():
            ok = False
    if ok:
        print("baton_pass: ALL PHASES PASS")
        return 0
    print("baton_pass: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
