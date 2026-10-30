"""intel/load_check.py -- INT-006 load check, scripted run.

A 2,000-message room plus a 200-job queue, built with real
commands on the in-memory fake surface, then three timed
operations: an ingest snapshot, a morning brief, and one
watchdog tick. The timings table lands in intel/evals/load.md
and the transcript in intel/evals/load.log.

What this run is, plainly:

- The queue is the in-memory fake Redis surface from
  tests/fake_redis.py, the same surface the unit suite uses.
  Nothing here touches the live bus or posts a real job. The
  job namespace is the INT-001 integration namespace
  (muse-bus:int-job), the capability namespace is
  muse-bus:int-cap, and the room is build-int, so even the
  fake state is disjoint from production keys.
- Every job is posted by a real jobs.py post command, and
  ten of them are claimed and progressed by a real worker
  through the real claim and progress commands, so the
  snapshot and the tick see a queue shaped like a real one:
  190 open jobs and 10 claimed jobs with fresh progress.
- The room list is seeded directly, after the queue, and
  this ordering is forced by a real product behavior the
  run discovered: every jobs announcement runs bus_trim,
  which keeps only the newest 500 messages
  (KEEP_MESSAGES), so a 2,000-message room is not
  reachable through the real announce path. The
  2,000-message state here is a beyond-cap stress state
  for the read path, not a room a live crew could build
  by posting, and the transcript says so.
- The snapshot is a real intel/ingest.py snapshot of that
  state, paged at 1,000 messages a page, so it reads all
  2,000 messages across three page reads. The brief is a
  real generate_brief call for kind morning, and the tick
  is a real watchdog.tick call on the same snapshot.
- The brief is a template brief (client None), not a Spark
  brief: GOV-001 leaves live Spark transport blocked, so
  the template path is the honest path here, and the
  transcript says TEMPLATE on its first line. The brief
  is built from the BRF-023 capped window (500 messages,
  24 hours), not from all 2,000 messages: the cap is the
  reason brief cost stays flat as the room grows, and the
  transcript says so.
- Timings are wall clock from time.perf_counter, not the
  fake clock: the fake clock never advances in this run,
  so every claimed job stays healthy and the tick must
  yield zero alerts. A nonzero alert count fails the run,
  because a healthy load room must not look like a stall.
- Budgets, stated here so the table can check against
  them: the plan documents no per-operation wall-clock
  budget for these three operations, so this check adopts
  one and records it. Each operation gets 5 seconds and
  the three together get 15 seconds. The 5 second figure
  is an order of magnitude inside the watchdog loop's
  documented 60 second default interval, so a tick that
  fits it can never fall behind the loop it feeds. The
  brief word budget is not adopted here: it is the plan's
  own FND-034 morning budget of 220 words, enforced by
  the template trim, and the run asserts the generated
  brief stays inside it.
- What the timings are not: sandbox wall times on an
  in-memory fake backend, not production hardware and
  not a live Redis round trip. They prove the shape of
  the cost (snapshot pages, brief caps, tick scans) at
  this scale, not a latency number for the demo machine.

Stages, each asserted, any failure failing the run:

  1. seed queue: 200 jobs posted, 10 claimed and
     progressed by the load worker, 190 left open.
  2. seed room: the room list cleared, then 2,000 plain
     messages seeded directly (see the bus_trim note
     above).
  3. snapshot: ingest.snapshot reads 2,000 messages and
     200 jobs, timed.
  4. brief: a morning template brief within 220 words,
     timed.
  5. tick: watchdog.tick on the snapshot yields zero
     alerts, timed.
  6. budgets: every timed operation and the three-operation
     total sit inside their adopted budgets.

Usage, from the repo root: python3 intel/load_check.py
Exit 0 with the transcript on stdout and in
intel/evals/load.log plus the table in intel/evals/load.md
when every stage passes, exit 1 otherwise. Importing
this module runs nothing: all setup (env, fake surface,
nicks, clock) happens inside run_check, and run_check
restores the job namespace, capability namespace, and
nicks it changed, so the unit suite can call it inside
its own harness.
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

MESSAGE_COUNT = 2000
JOB_COUNT = 200
CLAIMED_COUNT = 10
WORKER = "load-worker"
SNAPSHOT_BUDGET_SECONDS = 5.0
BRIEF_BUDGET_SECONDS = 5.0
TICK_BUDGET_SECONDS = 5.0
TOTAL_BUDGET_SECONDS = 15.0

LOG_PATH = os.path.join(ROOT, "intel", "evals", "load.log")
MD_PATH = os.path.join(ROOT, "intel", "evals", "load.md")

_STAGE_NAMES = ("seed queue", "seed room", "snapshot", "brief",
                "tick", "budgets")


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


def render_load_md(result):
    """Render the timings table markdown for a run_check result."""
    timings = result["timings"]
    budgets = result["budgets"]
    lines = [
        "# INT-006 load check",
        "",
        "2,000-message room + 200-job queue, timed on the "
        "in-memory fake surface (see intel/load_check.py). "
        "Timings are sandbox wall times, not production "
        "hardware and not a live Redis round trip.",
        "",
        "## Timings",
        "",
        "| Operation | Measured (s) | Budget (s) | Result |",
        "| --- | --- | --- | --- |",
    ]
    for name in ("snapshot", "brief", "tick"):
        measured = timings[name]
        budget = budgets[name]
        verdict = "PASS" if measured < budget else "FAIL"
        lines.append(f"| {name} | {measured:.3f} | {budget:.1f} "
                     f"| {verdict} |")
    total_verdict = ("PASS" if timings["total"] < budgets["total"]
                     else "FAIL")
    lines.append(f"| total (3 ops) | {timings['total']:.3f} "
                 f"| {budgets['total']:.1f} | {total_verdict} |")
    lines.extend([
        "",
        "## Counts",
        "",
        f"- Room messages in snapshot: {result['message_count']}",
        f"- Jobs in snapshot: {result['job_count']} "
        f"({result['claimed_count']} claimed with fresh progress, "
        f"{result['job_count'] - result['claimed_count']} open)",
        f"- Morning brief words: {result['brief_words']} "
        f"(FND-034 morning budget "
        f"{result['brief_word_budget']})",
        f"- Watchdog tick alerts: {result['alert_count']} "
        f"(healthy load room, zero expected)",
        "",
        "## Budgets",
        "",
        "The plan documents no per-operation wall-clock "
        "budget for snapshot, brief, or tick, so this check "
        "adopts one and records it here: 5 seconds per "
        "operation, 15 seconds for the three together. The "
        "5 second figure is an order of magnitude inside "
        "the watchdog loop's documented 60 second default "
        "interval, so a tick that fits it can never fall "
        "behind the loop it feeds. The brief word budget "
        "is the plan's own: FND-034 caps a morning brief "
        "at 220 words.",
        "",
        "## What this does not prove",
        "",
        "- A live-reachable 2,000-message room: every jobs "
        "announcement runs bus_trim, which keeps only the "
        "newest 500 messages, so the 2,000-message state "
        "here is a beyond-cap stress state for the read "
        "path, seeded directly after the queue.",
        "- A live Redis round trip: the fake backend has no "
        "network cost, so live timings will be higher.",
        "- A Spark-composed brief: the brief here is a "
        "template brief, because GOV-001 leaves live Spark "
        "transport blocked.",
        "- Alert behavior under load: the tick yields zero "
        "alerts here by design (every claimed job is "
        "healthy). Alert counts under a loaded, failing "
        "room are Milo's INT-023, not this check.",
        "",
    ])
    return "\n".join(lines)


def run_check(write_files=True):
    """Run the INT-006 load check; return the result dict.

    Returns {"ok": bool, "stages": [(name, ok, detail)], ...}.
    With write_files, the transcript goes to
    intel/evals/load.log and the table to intel/evals/load.md.
    Restores jobs.NS, capabilities.CAPNS, and the nicks it
    changed, so a caller inside another harness is
    unaffected.
    """
    # INT-001 import-order rule: the namespace variables must be
    # set before jobs (and mos.capabilities) are imported, or
    # the already-read prefixes do not move.
    integration.apply_env()
    import relay_common as rc  # noqa: E402
    import jobs  # noqa: E402
    from intel import brief  # noqa: E402
    from intel import ingest  # noqa: E402
    from intel import watchdog  # noqa: E402
    from mos import capabilities  # noqa: E402
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
    old_capns = capabilities.CAPNS
    old_nicks = (rc.NICK, jobs.NICK)
    fake = FakeUpstash()
    patches = [
        mock.patch.object(rc, "api_get", fake.api_get),
        mock.patch.object(rc, "api_post", fake.api_post),
        mock.patch.object(rc, "bus_push", fake.bus_push),
        mock.patch("time.time", fake.now),
    ]
    for mod in (jobs,):
        for attr in ("api_get", "api_post", "bus_push"):
            if hasattr(mod, attr):
                patches.append(mock.patch.object(
                    mod, attr, getattr(fake, attr)))
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
        # INT-001 import-order rule, second half: when jobs and
        # capabilities were already imported before this call
        # (as in the unit harness), setting the variables
        # cannot move the already-read prefixes, so assign
        # the integration prefixes explicitly. The finally
        # block below restores the old prefixes.
        assert os.environ.get("MUSE_RELAY_JOBNS") == \
            integration.INT_JOBNS
        assert os.environ.get("MUSE_RELAY_CAPNS") == \
            integration.INT_CAPNS
        jobs.NS = integration.INT_JOBNS
        capabilities.CAPNS = integration.INT_CAPNS

        holder = {}

        def do_seed_queue():
            rc.NICK = "pax"
            jobs.NICK = "pax"
            before = _job_list_json(jobs)
            assert before == [], f"job list not empty before: {before}"
            posted = []
            for number in range(1, JOB_COUNT + 1):
                spec = (f"Goal: finish load job {number}. Context: "
                        "INT-006 fixture. "
                        f"Files: intel/load_{number}.txt. Steps: "
                        "write the note. "
                        "Out of scope: any other file.")
                code, out, err = _run_cli(jobs.main, [
                    "post", "--title", f"Load job {number}",
                    "--spec", spec,
                    "--files", f"intel/load_{number}.txt",
                    "--max-attempts", "3",
                    "--room", integration.INT_ROOM])
                assert code == 0, f"post {number} failed: {err}"
                assert out.startswith("JOB "), (
                    f"unexpected post out: {out}")
                posted.append(out.split()[1])
            listed = _job_list_json(jobs)
            assert len(listed) == JOB_COUNT, (
                f"job list holds {len(listed)} jobs, "
                f"expected {JOB_COUNT}")
            assert capabilities.register(WORKER, ["python"]) is True
            rc.NICK = WORKER
            jobs.NICK = WORKER
            rc.presence_beat()
            for job_id in posted[:CLAIMED_COUNT]:
                code, _out, err = _run_cli(jobs.main, ["claim", job_id])
                assert code == 0, f"claim {job_id} failed: {err}"
                code, _out, err = _run_cli(jobs.main, [
                    "progress", job_id, "--note",
                    "load progress note"])
                assert code == 0, f"progress {job_id} failed: {err}"
            listed = _job_list_json(jobs)
            rows = {job["id"]: job for job in listed}
            claimed = [job_id for job_id in posted[:CLAIMED_COUNT]
                       if rows[job_id]["status"] == "claimed"]
            assert len(claimed) == CLAIMED_COUNT, (
                f"claimed {len(claimed)} jobs, "
                f"expected {CLAIMED_COUNT}")
            holder["posted"] = posted
            return (f"{JOB_COUNT} jobs posted, {CLAIMED_COUNT} "
                    "claimed and progressed, "
                    f"{JOB_COUNT - CLAIMED_COUNT} left open")

        stage("seed queue", do_seed_queue)

        def do_seed_room():
            # Seeded after the queue, and directly: every jobs
            # announcement above ran bus_trim, which keeps only
            # the newest 500 messages, so the list after the
            # queue holds at most 500 items. Clearing it and
            # pushing exactly 2,000 plain messages is the only
            # way to hold the task's 2,000-message state, and
            # that state is a beyond-cap stress state for the
            # read path, not a live-reachable room.
            key = rc.bus_key(integration.INT_ROOM)
            fake.lists[key] = []
            for index in range(MESSAGE_COUNT):
                fake.bus_push(
                    f"load-{index % 8}: load note {index}, "
                    "routine chatter, nothing to act on",
                    key=key)
            listed = fake.lists[key]
            assert len(listed) == MESSAGE_COUNT, (
                f"room list holds {len(listed)} messages, "
                f"expected {MESSAGE_COUNT}")
            return (f"{MESSAGE_COUNT} messages on the room list, "
                    "seeded directly after the bus_trim-capped "
                    "announcements")

        stage("seed room", do_seed_room)

        def do_snapshot():
            start = time.perf_counter()
            snapshot = ingest.snapshot(integration.INT_ROOM)
            elapsed = time.perf_counter() - start
            assert len(snapshot["messages"]) == MESSAGE_COUNT, (
                f"snapshot holds {len(snapshot['messages'])} "
                f"messages, expected {MESSAGE_COUNT}")
            assert len(snapshot["jobs"]) == JOB_COUNT, (
                f"snapshot holds {len(snapshot['jobs'])} jobs, "
                f"expected {JOB_COUNT}")
            holder["snapshot"] = snapshot
            holder["timings"] = {"snapshot": elapsed}
            return (f"snapshot read {MESSAGE_COUNT} messages and "
                    f"{JOB_COUNT} jobs in {elapsed:.3f}s")

        stage("snapshot", do_snapshot)

        def do_brief():
            snapshot = holder["snapshot"]
            start = time.perf_counter()
            text, stored = brief.generate_brief(
                snapshot, integration.INT_ROOM, kind="morning",
                now=int(fake.now()))
            elapsed = time.perf_counter() - start
            assert text.startswith("TEMPLATE"), (
                "morning brief here must be a template brief")
            words = len(text.split())
            budget = brief.BRIEF_BUDGETS["morning"]
            assert words <= budget, (
                f"morning brief over budget: {words} words")
            assert stored["kind"] == "morning", stored
            holder["timings"]["brief"] = elapsed
            holder["brief_words"] = words
            holder["brief_budget"] = budget
            holder["brief_text"] = text
            return (f"morning brief ({words} words, budget "
                    f"{budget}) in {elapsed:.3f}s, built from the "
                    "BRF-023 capped 500-message window")

        stage("brief", do_brief)

        def do_tick():
            snapshot = holder["snapshot"]
            start = time.perf_counter()
            got = watchdog.tick(snapshot, now=int(fake.now()))
            elapsed = time.perf_counter() - start
            assert got == [], (
                f"healthy load room must yield zero alerts, "
                f"got {len(got)}: {got}")
            holder["timings"]["tick"] = elapsed
            holder["alert_count"] = 0
            return (f"tick yielded zero alerts in {elapsed:.3f}s")

        stage("tick", do_tick)

        def do_budgets():
            timings = holder["timings"]
            timings["total"] = (timings["snapshot"] + timings["brief"]
                                + timings["tick"])
            budgets = {"snapshot": SNAPSHOT_BUDGET_SECONDS,
                       "brief": BRIEF_BUDGET_SECONDS,
                       "tick": TICK_BUDGET_SECONDS,
                       "total": TOTAL_BUDGET_SECONDS}
            for name in ("snapshot", "brief", "tick", "total"):
                assert timings[name] < budgets[name], (
                    f"{name} took {timings[name]:.3f}s, over its "
                    f"{budgets[name]:.1f}s budget")
            holder["timings"] = timings
            holder["budgets"] = budgets
            return (f"snapshot {timings['snapshot']:.3f}s, brief "
                    f"{timings['brief']:.3f}s, tick "
                    f"{timings['tick']:.3f}s, total "
                    f"{timings['total']:.3f}s, all inside budget")

        stage("budgets", do_budgets)
    finally:
        for patch in reversed(patches):
            patch.stop()
        jobs.NS = old_ns
        capabilities.CAPNS = old_capns
        rc.NICK, jobs.NICK = old_nicks

    ok = (len(stages) == len(_STAGE_NAMES)
          and all(passed for _name, passed, _d in stages))
    result["ok"] = ok
    if ok:
        result["message_count"] = MESSAGE_COUNT
        result["job_count"] = JOB_COUNT
        result["claimed_count"] = CLAIMED_COUNT
        result["brief_words"] = holder["brief_words"]
        result["brief_word_budget"] = holder["brief_budget"]
        result["alert_count"] = holder["alert_count"]
        result["timings"] = holder["timings"]
        result["budgets"] = holder["budgets"]
        result["brief_text"] = holder["brief_text"]

    lines = ["INT-006 load check",
             f"room: {MESSAGE_COUNT} messages, queue: {JOB_COUNT} "
             f"jobs ({CLAIMED_COUNT} claimed, "
             f"{JOB_COUNT - CLAIMED_COUNT} open)",
             ("queue: in-memory fake surface, namespace "
              f"{integration.INT_JOBNS}, caps "
              f"{integration.INT_CAPNS}, room {integration.INT_ROOM}"),
             ("clock: fake clock never advanced, so every claimed "
              "job stays healthy and the tick must yield zero "
              "alerts; timings are perf_counter wall times"),
             ("brief: template path (no live Spark call; GOV-001 "
              "leaves live transport blocked), built from the "
              "BRF-023 capped 500-message window"),
             ""]
    for name, passed, detail in stages:
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    lines.append("")
    lines.append("INT-006: " + ("PASS (all stages)"
                                if ok else "FAIL"))
    transcript = "\n".join(lines) + "\n"
    result["transcript"] = transcript
    if ok:
        result["table"] = render_load_md(result)
    if write_files:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as handle:
            handle.write(transcript)
        if ok:
            with open(MD_PATH, "w") as handle:
                handle.write(result["table"])
    return result


def main():
    """Run the check, print the transcript, exit 0/1."""
    result = run_check(write_files=True)
    sys.stdout.write(result["transcript"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
