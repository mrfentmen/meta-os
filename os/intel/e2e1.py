"""intel/e2e1.py -- INT-002 end-to-end test 1, scripted loop.

Goal -> dispatch dry-run -> approve -> post -> worker claims ->
done -> brief reports it, as one scripted run with a transcript
written to intel/evals/e2e1.log.

What this run is, plainly:

- The loop starts from a hand-authored plan JSON, exactly what the
  DSP-006 dry-run consumes. The live goal -> plan Spark call is
  NOT part of this loop: GOV-001 leaves the live Spark transport
  blocked, and inventing a Spark answer here would break the
  no-invention rule. DSP-017 covers that seam (plan_from_spark
  with a caller-supplied callable); this script proves the loop
  from a validated plan onward, and says so in the transcript.
- The queue is the in-memory fake Redis surface from
  tests/fake_redis.py, the same surface the unit suite uses.
  Nothing here touches the live bus, posts a real job, or spends
  Spark credit. The job namespace is the INT-001 integration
  namespace (muse-bus:int-job), and the room is build-int, so
  even the fake state is disjoint from production keys.
- The worker steps are the real jobs.py claim/progress/done
  commands, run as nick worker-a, in posting order. The mos
  worker loop itself is DSP-019's proven chain and is not
  re-proven here; the queue-level claim is what this loop
  asserts.
- The brief step uses shipped brief machinery only: a snapshot
  from intel/ingest.py, then a boot brief carrying the
  OS-051 previous-session digest over the final job list. The
  template brief's "In flight" section lists open/claimed jobs,
  never done ones, so a done job is reported the way the
  product reports it: the digest line "N jobs completed
  (titles)". The script asserts that line, not a paraphrase.

Stages, each asserted, any failure failing the run:

  1. dry-run: dry_run_plan renders both jobs in posting order
     probe -> report, and the job list is empty before and after
     (a dry-run posts nothing).
  2. approve: request_approval with approve=True passes, and
     with no approval at all it denies (approval is never
     manufactured by the script).
  3. post: post_plan posts both jobs in order, stores one
     dispatch record, and reports signed=False with the loud
     unsigned warning on stderr (no keyring in this loop, crew
     mode off, exactly the DSP-009 unsigned path).
  4. worker probe: worker-a claims, progresses, and finishes
     the probe job; show_dispatch then reads probe done,
     report open.
  5. worker report: worker-a claims, progresses, and finishes
     the report job; show_dispatch then reads both done.
  6. brief: the snapshot carries both jobs done, the "In
     flight" section of a fresh template brief reads nothing
     reported, and a boot brief over the same snapshot plus
     the previous-session digest reports "2 jobs completed"
     with both titles.

Usage, from the repo root: python3 intel/e2e1.py
Exit 0 with the transcript on stdout and in
intel/evals/e2e1.log when every stage passes, exit 1
otherwise. Importing this module runs nothing: all setup
(env, fake surface, nicks) happens inside run_loop, and
run_loop restores the job namespace and nicks it changed,
so the unit suite can call it inside its own harness.
"""

import contextlib
import io
import json
import os
import sys
import time
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from intel import integration  # noqa: E402

GOAL = ("Probe the snapshot path, then report the result in "
        "the brief.")

PLAN_JSON = json.dumps({
    "summary": "Probe the snapshot path, then report it in the brief.",
    "jobs": [
        {
            "key": "probe",
            "title": "Write the e2e probe note",
            "spec": ("Goal: prove the loop. Context: INT-002 "
                     "fixture. Files: intel/e2e1_probe.txt. "
                     "Steps: write the note. Out of scope: any "
                     "other file."),
            "files": ["intel/e2e1_probe.txt"],
            "deps": [],
            "max_attempts": 3,
            "accept": ["file-exists: intel/e2e1_probe.txt"],
        },
        {
            "key": "report",
            "title": "Record the probe result in the e2e log",
            "spec": ("Goal: close the loop. Context: INT-002 "
                     "fixture. Files: intel/evals/e2e1.log. "
                     "Steps: append the probe result. Out of "
                     "scope: any other file."),
            "files": ["intel/evals/e2e1.log"],
            "deps": ["probe"],
            "max_attempts": 3,
            "accept": ["contains: intel/evals/e2e1.log :: probe"],
        },
    ],
})

LOG_PATH = os.path.join(ROOT, "intel", "evals", "e2e1.log")

_STAGE_NAMES = ("dry-run", "approve", "post", "worker probe",
                "worker report", "brief")


def _run_cli(main, argv):
    """Run a script main(); return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err), \
            mock.patch("sys.stdin", io.StringIO("")):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _job_list_json(jobs_mod):
    code, out, _err = _run_cli(jobs_mod.main, ["list", "--json"])
    if code != 0:
        raise AssertionError(f"jobs list failed with exit {code}")
    return json.loads(out)


def run_loop(write_log=True):
    """Run the INT-002 loop; return the result dict.

    Returns {"ok": bool, "stages": [(name, ok, detail)], ...}.
    With write_log, the transcript is also written to
    intel/evals/e2e1.log. Restores jobs.NS and the nicks it
    changed, so a caller inside another harness is unaffected.
    """
    # INT-001 import-order rule: the namespace variables must be
    # set before jobs (and mos.capabilities) are imported, or
    # the already-read prefixes do not move.
    integration.apply_env()
    import relay_common as rc  # noqa: E402
    import jobs  # noqa: E402
    from intel import brief as brief_mod  # noqa: E402
    from intel import dispatch  # noqa: E402
    from intel import ingest  # noqa: E402
    from fake_redis import FakeUpstash  # noqa: E402

    stages = []

    def stage(name, fn):
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - a stage
            # failure is a loop failure, reported, not traced
            stages.append((name, False, f"{type(exc).__name__}: {exc}"))
            return None
        stages.append((name, True, detail))
        return detail

    old_ns = jobs.NS
    old_nicks = (rc.NICK, jobs.NICK)
    fake = FakeUpstash()
    patches = [
        mock.patch.object(rc, "api_get", fake.api_get),
        mock.patch.object(rc, "api_post", fake.api_post),
        mock.patch.object(rc, "bus_push", fake.bus_push),
    ]
    for mod in (jobs,):
        for attr in ("api_get", "api_post", "bus_push"):
            if hasattr(mod, attr):
                patches.append(mock.patch.object(
                    mod, attr, getattr(fake, attr)))
    # intel.store and intel.ingest reach the bus through
    # relay_common's names; patching relay_common covers them,
    # but modules that did `from relay_common import api_get`
    # hold their own reference, so patch those too.
    import intel.store as store_mod  # noqa: E402
    import intel.ingest as ingest_mod  # noqa: E402
    for mod in (store_mod, ingest_mod):
        for attr in ("api_get", "api_post", "bus_push"):
            if hasattr(mod, attr):
                patches.append(mock.patch.object(
                    mod, attr, getattr(fake, attr)))
    result = {"ok": False, "stages": stages}
    try:
        for patch in patches:
            patch.start()
        # INT-001 import-order rule, second half: when jobs was
        # already imported before this call (as in the unit
        # harness, where jobs.NS is the test prefix), setting
        # the variables cannot move the already-read prefix,
        # so assign the integration prefix explicitly. The env
        # assignment above covers the fresh-import path; the
        # explicit assignment covers the already-imported path.
        # The finally block below restores the old prefix.
        assert os.environ.get("MUSE_RELAY_JOBNS") == \
            integration.INT_JOBNS
        jobs.NS = integration.INT_JOBNS

        def do_dry_run():
            before = _job_list_json(jobs)
            assert before == [], f"job list not empty before: {before}"
            detail = dispatch.dry_run_plan(PLAN_JSON)
            assert "Write the e2e probe note" in detail
            assert "Record the probe result in the e2e log" in detail
            assert "jobs in posting order: probe -> report" in detail
            after = _job_list_json(jobs)
            assert after == [], f"dry-run posted jobs: {after}"
            return ("rendered probe -> report in posting order; "
                    "job list empty before and after")

        stage("dry-run", do_dry_run)

        plan_holder = {}

        def do_approve():
            plan, order, clamps = dispatch.validated_plan(PLAN_JSON)
            assert order == ["probe", "report"], f"order {order}"
            assert clamps == [], f"unexpected clamps {clamps}"
            assert dispatch.request_approval(plan, approve=True) is True
            assert dispatch.request_approval(plan) is False, (
                "approval without a human must deny")
            plan_holder["plan"] = plan
            plan_holder["order"] = order
            return "validated plan, order probe -> report, no clamps"

        stage("approve", do_approve)

        record_holder = {}

        def do_post():
            rc.NICK = "pax"
            jobs.NICK = "pax"
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                record = dispatch.post_plan(
                    plan_holder["plan"], plan_holder["order"],
                    room=integration.INT_ROOM)
            assert "posting unsigned" in err.getvalue(), (
                "unsigned post must warn loudly on stderr")
            assert record["signed"] is False
            keys = [job["key"] for job in record["jobs"]]
            assert keys == ["probe", "report"], f"posted keys {keys}"
            ids = {job["key"]: job["id"] for job in record["jobs"]}
            assert ids["report"] != ids["probe"]
            listed = _job_list_json(jobs)
            by_id = {job["id"]: job for job in listed}
            assert by_id[ids["probe"]]["status"] == "open"
            assert by_id[ids["report"]]["status"] == "open"
            assert by_id[ids["report"]]["deps"] == ids["probe"], (
                "report must carry the real probe id as its dep")
            record_holder["record"] = record
            record_holder["ids"] = ids
            return (f"dispatch {record['id']}: probe -> "
                    f"{ids['probe']}, report -> {ids['report']}, "
                    f"signed=False with the unsigned warning")

        stage("post", do_post)

        def do_worker(key, note, expected):
            rc.NICK = "worker-a"
            jobs.NICK = "worker-a"
            job_id = record_holder["ids"][key]
            code, _out, err = _run_cli(jobs.main, ["claim", job_id])
            assert code == 0, f"claim {key} failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["progress", job_id, "--note", note])
            assert code == 0, f"progress {key} failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["done", job_id,
                            "--commit", "e2e1-no-real-commit",
                            "--note", note])
            assert code == 0, f"done {key} failed: {err}"
            report = dispatch.show_dispatch(
                record_holder["record"]["id"])
            by_key = {job["key"]: job["status"]
                      for job in report["jobs"]}
            assert by_key == expected, (
                f"show after {key} done reads {by_key}, "
                f"expected {expected}")
            return (f"{key} claimed, progressed, done as worker-a; "
                    f"show reads {by_key}")

        stage("worker probe",
              lambda: do_worker("probe", "probe note written",
                                {"probe": "done", "report": "open"}))
        stage("worker report",
              lambda: do_worker("report", "probe result recorded",
                                {"probe": "done", "report": "done"}))

        def do_brief():
            snapshot = ingest.snapshot(integration.INT_ROOM)
            # INT-024 follow-up (Hana, route a): cap the snapshot
            # through the BRF-023 window cap before composing, so
            # both e2e briefs state their window instead of
            # reading "not stated". This touches Pax's e2e script;
            # the cap is Hana's BRF-023 helper, defaults unchanged
            # (last 500 messages or last 24 hours).
            snapshot = brief_mod.cap_snapshot_window(snapshot)
            # INT-024 fix: route the brief stage through the
            # BRF-023 cap, so the brief carries a stated window
            # instead of "Window: not stated in this snapshot".
            # The cap states the cap (500 messages / 24 hours);
            # it invents no history. On this loop it keeps all
            # 8 messages and drops 0, so no brief fact changes.
            snapshot = brief_mod.cap_snapshot_window(snapshot)
            assert isinstance(snapshot.get("source_window"), dict), (
                "e2e brief stage must carry a BRF-023 window record")
            snap_jobs = {job["id"]: job
                         for job in snapshot.get("jobs", [])}
            ids = record_holder["ids"]
            assert snap_jobs[ids["probe"]]["status"] == "done"
            assert snap_jobs[ids["report"]]["status"] == "done"
            plain = brief_mod.compose_template_brief(snapshot)
            in_flight = plain.split("In flight")[1].split("Owners")[0]
            assert "Nothing reported in this window" in in_flight, (
                "no job may read in flight once both are done")
            prev = brief_mod.build_previous_session(
                {"generated_at": int(time.time())},
                snapshot.get("jobs", []))
            assert prev is not None
            digest = brief_mod.previous_session_digest(prev)
            assert digest is not None
            assert "2 jobs completed" in digest, digest
            assert "Write the e2e probe note" in digest, digest
            assert "Record the probe result in the e2e log" in digest
            boot = brief_mod.compose_template_brief(
                dict(snapshot, previous_session=prev), boot=True)
            assert digest in boot, "boot brief must carry the digest"
            return (f"snapshot carries both jobs done; boot brief "
                    f"reports: {digest}")

        stage("brief", do_brief)
    finally:
        for patch in reversed(patches):
            patch.stop()
        jobs.NS = old_ns
        rc.NICK, jobs.NICK = old_nicks

    ok = (len(stages) == len(_STAGE_NAMES)
          and all(passed for _name, passed, _d in stages))
    result["ok"] = ok
    if ok:
        result["dispatch_id"] = record_holder["record"]["id"]
        result["job_ids"] = record_holder["ids"]

    lines = ["INT-002 end-to-end test 1",
             f"goal: {GOAL}",
             ("plan: hand-authored fixture (no live Spark call; "
              "see module docstring)"),
             ("queue: in-memory fake surface, namespace "
              f"{integration.INT_JOBNS}, room {integration.INT_ROOM}"),
             ""]
    for name, passed, detail in stages:
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    lines.append("")
    lines.append("INT-002: " + ("PASS (all stages)"
                                if ok else "FAIL"))
    transcript = "\n".join(lines) + "\n"
    result["transcript"] = transcript
    if write_log:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as handle:
            handle.write(transcript)
    return result


def main():
    """Run the loop, print the transcript, exit 0/1."""
    result = run_loop(write_log=True)
    sys.stdout.write(result["transcript"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
