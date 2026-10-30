"""intel/watchdog_load_check.py -- INT-023 watchdog-under-load check.

A 200-job queue under failure, built with real commands on the
in-memory fake surface, then three watchdog ticks: the first
over a loaded, failing room, the second inside the alert
dedupe cooldown, the third after the workers recover. The
table lands in intel/evals/watchdog_load.md and the
transcript in intel/evals/watchdog_load.log.

What this run is, plainly:

- The queue is the in-memory fake Redis surface from
  tests/fake_redis.py, the same surface the unit suite and
  the INT-006 load check use. Nothing here touches the
  live bus or posts a real job. The job namespace is the
  INT-001 integration namespace (muse-bus:int-job), the
  capability namespace is muse-bus:int-cap, and the room
  is build-int, so even the fake state is disjoint from
  production keys.
- Every job is posted by a real jobs.py post command with
  a unique files path (so no two jobs collide), no deps
  (so no dead-dep or missing-dep noise), and max_attempts
  3 with zero attempts burned (so no attempt noise).
  Fifty jobs are claimed: 25 by a worker that then goes
  silent (presence lapses, progress stops) and 25 by a
  worker that stays present but stops progressing. The
  other 150 jobs stay open. The fake clock then advances
  61 minutes: past the 10-minute stall thresholds, past
  the 30-minute claim leases (so no lease-risk warning
  fires for an already-expired lease), and past the
  120-second presence TTL (so the silent worker is
  genuinely absent from presence, not merely quiet).
- The room list is seeded directly with 2,000 plain
  messages after the queue, exactly like INT-006: every
  jobs announcement runs bus_trim, which keeps only the
  newest 500 messages, so a 2,000-message room is a
  beyond-cap stress state for the read path, not a room a
  live crew could build by posting. Plain strings carry
  no timestamp, so the WDG-009 silent-room detector
  stays silent, and none of them is a REJECTED line, so
  the INT-010 detector stays silent too. The point of
  the 2,000 messages is the negative: message volume
  must not multiply the alert count.
- Tick 1 must yield exactly 50 alerts: 25
  presence-stall (one per silent worker job) and 25
  progress-stall (one per stuck worker job), one alert
  per stalled job and no alert of any other kind. That
  is the no-alert-storm half: 50 stalled jobs produce
  50 alerts, not 50 times anything, and 150 healthy
  open jobs plus 2,000 messages produce zero.
- Tick 2 runs 5 minutes later, inside the 30-minute
  WDG-013 dedupe cooldown, with the stuck worker's
  presence re-beaten so its kind does not flip. The
  detectors re-fire the same 50 alerts (a tick reports
  what it sees), but writing them through
  intel.store.write_alert must NOT grow the store: the
  record count stays 50, every record keeps its tick-1
  created_at, and every record's last_seen advances to
  the tick-2 time. That is the dedupe-holds half.
- Tick 3 runs after both workers post a fresh progress
  note on every claimed job (real progress commands,
  which re-acquire the lapsed lease mutex) and re-beat
  presence. It must yield zero alerts: the detectors
  stop firing when the condition clears. Tick silence
  is not store resolution — the 50 records stay in the
  alert store until the WDG-014 lifecycle resolves
  them, and this check does not claim otherwise.
- Budgets, stated here so the table can check against
  them: the plan documents no per-tick wall-clock
  budget, so this check adopts INT-006's: 5 seconds
  per tick, 15 seconds for the three together. Timings
  are wall clock from time.perf_counter, not the fake
  clock: the fake clock is the scenario clock (ages,
  TTLs, cooldowns), the wall clock is the cost clock.

Stages, each asserted, any failure failing the run:

  1. seed queue: 200 jobs posted, 50 claimed (25
     silent, 25 stuck), 150 left open, clock +61 min.
  2. seed room: 2,000 plain messages seeded directly
     after the bus_trim-capped announcements.
  3. tick 1: exactly 50 stall alerts, 50 stored records.
  4. tick 2: same 50 detector alerts, store still 50,
     last_seen advanced, created_at unchanged.
  5. tick 3: workers recovered, zero alerts.
  6. budgets: every tick and the three-tick total sit
     inside their adopted budgets.

Usage, from the repo root: python3 intel/watchdog_load_check.py
Exit 0 with the transcript on stdout and in
intel/evals/watchdog_load.log plus the table in
intel/evals/watchdog_load.md when every stage passes,
exit 1 otherwise. Importing this module runs nothing:
all setup (env, fake surface, nicks, clock) happens
inside run_check, and run_check restores the job
namespace, capability namespace, and nicks it changed,
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

MESSAGE_COUNT = 2000
JOB_COUNT = 200
SILENT_COUNT = 25
STUCK_COUNT = 25
CLAIMED_COUNT = SILENT_COUNT + STUCK_COUNT
SILENT_WORKER = "load-silent"
STUCK_WORKER = "load-stuck"
ADVANCE_SECONDS = 3660
REBEAT_GAP_SECONDS = 300
TICK_BUDGET_SECONDS = 5.0
TOTAL_BUDGET_SECONDS = 15.0

LOG_PATH = os.path.join(ROOT, "intel", "evals", "watchdog_load.log")
MD_PATH = os.path.join(ROOT, "intel", "evals", "watchdog_load.md")

_STAGE_NAMES = ("seed queue", "seed room", "tick 1 stalled load",
                "tick 2 dedupe", "tick 3 cleared", "budgets")


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


def render_watchdog_load_md(result):
    """Render the counts table markdown for a run_check result."""
    ticks = result["ticks"]
    lines = [
        "# INT-023 watchdog under load",
        "",
        "200-job queue under failure, three ticks on the "
        "in-memory fake surface (see "
        "intel/watchdog_load_check.py). Timings are sandbox "
        "wall times, not production hardware and not a live "
        "Redis round trip.",
        "",
        "## Counts",
        "",
        "| Tick | Detector alerts | Stored records | "
        "Kinds |",
        "| --- | --- | --- | --- |",
        f"| 1 (stalled load) | {ticks[0]['alerts']} | "
        f"{ticks[0]['stored']} | "
        f"{ticks[0]['kinds']} |",
        f"| 2 (inside cooldown) | {ticks[1]['alerts']} | "
        f"{ticks[1]['stored']} | "
        f"{ticks[1]['kinds']} |",
        f"| 3 (workers recovered) | {ticks[2]['alerts']} | "
        f"{ticks[2]['stored']} | "
        f"{ticks[2]['kinds']} |",
        "",
        "## What the three ticks prove",
        "",
        "- No alert storm: 50 stalled jobs yield exactly "
        "50 alerts on tick 1 (25 presence-stall, 25 "
        "progress-stall), one per stalled job; 150 open "
        "jobs and 2,000 room messages yield zero more.",
        "- Dedupe holds: tick 2, inside the 30-minute "
        "cooldown, re-fires the same 50 detector alerts "
        "but the store stays at 50 records, every "
        "record keeping its tick-1 created_at with "
        "last_seen advanced to the tick-2 time.",
        "- Silence on recovery: tick 3, after fresh "
        "progress notes from both workers, yields zero "
        "alerts. The 50 tick-1 records remain in the "
        "store until the WDG-014 lifecycle resolves "
        "them; tick silence is not store resolution.",
        "",
        "## Timings",
        "",
        "| Tick | Measured (s) | Budget (s) | Result |",
        "| --- | --- | --- | --- |",
    ]
    for index, tick in enumerate(ticks, start=1):
        verdict = "PASS" if tick["seconds"] < TICK_BUDGET_SECONDS \
            else "FAIL"
        lines.append(f"| {index} | {tick['seconds']:.3f} | "
                     f"{TICK_BUDGET_SECONDS:.1f} | {verdict} |")
    total = result["timings"]["total"]
    total_verdict = "PASS" if total < TOTAL_BUDGET_SECONDS \
        else "FAIL"
    lines.append(f"| total (3 ticks) | {total:.3f} | "
                 f"{TOTAL_BUDGET_SECONDS:.1f} | {total_verdict} |")
    lines.extend([
        "",
        "## Budgets",
        "",
        "The plan documents no per-tick wall-clock budget, "
        "so this check adopts INT-006's: 5 seconds per "
        "tick, 15 seconds for the three together. The 5 "
        "second figure is an order of magnitude inside "
        "the watchdog loop's documented 60 second default "
        "interval, so a tick that fits it can never fall "
        "behind the loop it feeds.",
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
        "- A Spark-composed brief or polished explanations: "
        "no Spark client is passed to any tick here, so "
        "every alert carries its WDG-011 template text.",
        "- Store resolution on recovery: tick 3 proves the "
        "detectors stop firing, not that the WDG-014 "
        "lifecycle marks the 50 records resolved.",
        "",
    ])
    return "\n".join(lines)


def run_check(write_files=True):
    """Run the INT-023 watchdog-under-load check; return result.

    Returns {"ok": bool, "stages": [(name, ok, detail)], ...}.
    With write_files, the transcript goes to
    intel/evals/watchdog_load.log and the table to
    intel/evals/watchdog_load.md. Restores jobs.NS,
    capabilities.CAPNS, and the nicks it changed, so the
    unit suite can call it inside its own harness.
    """
    # INT-001 import-order rule: the namespace variables must be
    # set before jobs (and mos.capabilities) are imported, or
    # the already-read prefixes do not move.
    integration.apply_env()
    import relay_common as rc  # noqa: E402
    import jobs  # noqa: E402
    from intel import ingest  # noqa: E402
    from intel import store as store_mod  # noqa: E402
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
    for mod in (store_mod, ingest):
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

        def _post_and_claim():
            rc.NICK = "pax"
            jobs.NICK = "pax"
            before = _job_list_json(jobs)
            assert before == [], f"job list not empty before: {before}"
            posted = []
            for number in range(1, JOB_COUNT + 1):
                spec = (f"Goal: finish load job {number}. Context: "
                        "INT-023 fixture. "
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
            assert capabilities.register(SILENT_WORKER,
                                         ["python"]) is True
            assert capabilities.register(STUCK_WORKER,
                                         ["python"]) is True
            groups = [(SILENT_WORKER, posted[:SILENT_COUNT]),
                      (STUCK_WORKER,
                       posted[SILENT_COUNT:CLAIMED_COUNT])]
            for worker, job_ids in groups:
                rc.NICK = worker
                jobs.NICK = worker
                rc.presence_beat()
                for job_id in job_ids:
                    code, _out, err = _run_cli(jobs.main,
                                               ["claim", job_id])
                    assert code == 0, f"claim {job_id} failed: {err}"
                    code, _out, err = _run_cli(jobs.main, [
                        "progress", job_id, "--note",
                        "load progress note"])
                    assert code == 0, (
                        f"progress {job_id} failed: {err}")
            listed = _job_list_json(jobs)
            rows = {job["id"]: job for job in listed}
            claimed = [job_id for job_id in posted[:CLAIMED_COUNT]
                       if rows[job_id]["status"] == "claimed"]
            assert len(claimed) == CLAIMED_COUNT, (
                f"claimed {len(claimed)} jobs, "
                f"expected {CLAIMED_COUNT}")
            holder["posted"] = posted
            holder["silent_ids"] = set(posted[:SILENT_COUNT])
            holder["stuck_ids"] = set(
                posted[SILENT_COUNT:CLAIMED_COUNT])
            return (f"{JOB_COUNT} jobs posted, {CLAIMED_COUNT} "
                    f"claimed ({SILENT_COUNT} silent, "
                    f"{STUCK_COUNT} stuck), "
                    f"{JOB_COUNT - CLAIMED_COUNT} left open")

        def do_seed_queue():
            detail = _post_and_claim()
            # 61 minutes: past the 10-minute stall
            # thresholds, past the 30-minute claim leases
            # (so no lease-risk warning for an already
            # expired lease), past the 120-second presence
            # TTL (so the silent worker is absent from
            # presence). The stuck worker re-beats below,
            # before each tick that must see it present.
            fake.advance(ADVANCE_SECONDS)
            return detail + f", clock advanced {ADVANCE_SECONDS}s"

        stage("seed queue", do_seed_queue)

        def do_seed_room():
            # Seeded after the queue, and directly: every jobs
            # announcement above ran bus_trim, which keeps
            # only the newest 500 messages, so the list
            # after the queue holds at most 500 items.
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

        def _tick_and_store():
            # The stuck worker must be present for the
            # progress-stall kind; the silent worker must
            # stay silent for the presence-stall kind.
            rc.NICK = STUCK_WORKER
            jobs.NICK = STUCK_WORKER
            rc.presence_beat()
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert len(snapshot["jobs"]) == JOB_COUNT, (
                f"snapshot holds {len(snapshot['jobs'])} jobs, "
                f"expected {JOB_COUNT}")
            start = time.perf_counter()
            alerts = watchdog.tick(snapshot, now=int(fake.now()))
            elapsed = time.perf_counter() - start
            kinds = {}
            for alert in alerts:
                kinds[alert["kind"]] = kinds.get(
                    alert["kind"], 0) + 1
            stored = [store_mod.write_alert(
                alert, room=integration.INT_ROOM)
                for alert in alerts]
            return snapshot, alerts, kinds, stored, elapsed

        def do_tick1():
            _snapshot, alerts, kinds, stored, elapsed = \
                _tick_and_store()
            assert len(alerts) == CLAIMED_COUNT, (
                f"tick 1 yielded {len(alerts)} alerts, "
                f"expected {CLAIMED_COUNT}")
            assert kinds == {"presence-stall": SILENT_COUNT,
                             "progress-stall": STUCK_COUNT}, (
                f"tick 1 kinds {kinds}, expected 25 "
                "presence-stall + 25 progress-stall")
            by_job = {}
            for alert in alerts:
                by_job.setdefault(alert["job"], []).append(
                    alert["kind"])
            assert all(len(v) == 1 for v in by_job.values()), (
                "a stalled job yielded more than one alert")
            assert {a["job"] for a in alerts} == \
                holder["silent_ids"] | holder["stuck_ids"], (
                "tick 1 alert jobs are not exactly the "
                "claimed jobs")
            assert {a["job"] for a in alerts
                    if a["kind"] == "presence-stall"} == \
                holder["silent_ids"], (
                "presence-stall jobs are not the silent "
                "worker's jobs")
            assert {a["job"] for a in alerts
                    if a["kind"] == "progress-stall"} == \
                holder["stuck_ids"], (
                "progress-stall jobs are not the stuck "
                "worker's jobs")
            queried = store_mod.query_alerts(
                room=integration.INT_ROOM)
            assert len(queried) == CLAIMED_COUNT, (
                f"store holds {len(queried)} records after "
                f"tick 1, expected {CLAIMED_COUNT}")
            holder["tick1_now"] = int(fake.now())
            holder["tick1_ids"] = [rec["id"] for rec in stored]
            holder["tick1_keys"] = sorted(
                a["dedupe_key"] for a in alerts)
            holder["ticks"] = [{
                "alerts": len(alerts),
                "stored": len(queried),
                "kinds": "25 presence-stall, 25 progress-stall",
                "seconds": elapsed}]
            return (f"tick 1: {len(alerts)} alerts "
                    f"({kinds}), {len(queried)} records "
                    f"stored, in {elapsed:.3f}s")

        stage("tick 1 stalled load", do_tick1)

        def do_tick2():
            # 5 minutes later: inside the 30-minute dedupe
            # cooldown, so re-fired alerts must update
            # last_seen, not create records.
            fake.advance(REBEAT_GAP_SECONDS)
            _snapshot, alerts, kinds, stored, elapsed = \
                _tick_and_store()
            assert len(alerts) == CLAIMED_COUNT, (
                f"tick 2 yielded {len(alerts)} alerts, "
                f"expected {CLAIMED_COUNT}")
            assert kinds == {"presence-stall": SILENT_COUNT,
                             "progress-stall": STUCK_COUNT}, (
                f"tick 2 kinds {kinds} differ from tick 1")
            assert sorted(a["dedupe_key"] for a in alerts) == \
                holder["tick1_keys"], (
                "tick 2 dedupe keys differ from tick 1: "
                "the same incidents must re-fire under the "
                "same keys for dedupe to apply")
            queried = store_mod.query_alerts(
                room=integration.INT_ROOM)
            assert len(queried) == CLAIMED_COUNT, (
                f"store holds {len(queried)} records after "
                f"tick 2, expected still {CLAIMED_COUNT}")
            tick2_now = int(fake.now())
            for rec in stored:
                reread = store_mod.get_alert(rec["id"])
                assert reread is not None, (
                    f"record {rec['id']} vanished on tick 2")
                assert reread["created_at"] == \
                    holder["tick1_now"], (
                    f"record {rec['id']} created_at moved on "
                    "tick 2: dedupe must keep tick-1 creation")
                assert reread["last_seen"] == tick2_now, (
                    f"record {rec['id']} last_seen "
                    f"{reread['last_seen']} != tick-2 time "
                    f"{tick2_now}: dedupe must advance it")
            holder["ticks"].append({
                "alerts": len(alerts),
                "stored": len(queried),
                "kinds": "25 presence-stall, 25 progress-stall",
                "seconds": elapsed})
            return (f"tick 2: {len(alerts)} detector alerts, "
                    f"store still {len(queried)} records, "
                    f"last_seen advanced to tick-2 time, "
                    f"in {elapsed:.3f}s")

        stage("tick 2 dedupe", do_tick2)

        def do_tick3():
            # Both workers recover through real progress
            # commands (which re-acquire the lapsed lease
            # mutex) and fresh presence beats; the
            # detectors must then stop firing. The 50
            # store records remain: tick silence is not
            # WDG-014 resolution, and this stage does not
            # claim it.
            groups = [(SILENT_WORKER, holder["posted"][:SILENT_COUNT]),
                      (STUCK_WORKER,
                       holder["posted"][SILENT_COUNT:CLAIMED_COUNT])]
            for worker, job_ids in groups:
                rc.NICK = worker
                jobs.NICK = worker
                rc.presence_beat()
                for job_id in job_ids:
                    code, _out, err = _run_cli(jobs.main, [
                        "progress", job_id, "--note",
                        "load recovered progress"])
                    assert code == 0, (
                        f"recovery progress {job_id} failed: "
                        f"{err}")
            snapshot = ingest.snapshot(integration.INT_ROOM)
            start = time.perf_counter()
            alerts = watchdog.tick(snapshot, now=int(fake.now()))
            elapsed = time.perf_counter() - start
            assert alerts == [], (
                f"tick 3 yielded {len(alerts)} alerts after "
                f"recovery, expected zero: {alerts[:3]}")
            queried = store_mod.query_alerts(
                room=integration.INT_ROOM)
            assert len(queried) == CLAIMED_COUNT, (
                f"store holds {len(queried)} records after "
                f"tick 3, expected the tick-1 {CLAIMED_COUNT} "
                "still standing (tick silence is not "
                "resolution)")
            holder["ticks"].append({
                "alerts": 0,
                "stored": len(queried),
                "kinds": "none",
                "seconds": elapsed})
            return (f"tick 3: zero alerts after recovery, "
                    f"store still holds {len(queried)} "
                    f"tick-1 records, in {elapsed:.3f}s")

        stage("tick 3 cleared", do_tick3)

        def do_budgets():
            timings = {"total": sum(t["seconds"]
                                    for t in holder["ticks"])}
            budgets = {"total": TOTAL_BUDGET_SECONDS}
            for tick in holder["ticks"]:
                assert tick["seconds"] < TICK_BUDGET_SECONDS, (
                    f"a tick took {tick['seconds']:.3f}s, over "
                    f"its {TICK_BUDGET_SECONDS:.1f}s budget")
            assert timings["total"] < TOTAL_BUDGET_SECONDS, (
                f"three ticks took {timings['total']:.3f}s, "
                f"over the {TOTAL_BUDGET_SECONDS:.1f}s budget")
            holder["timings"] = timings
            holder["budgets"] = budgets
            return (f"ticks "
                    f"{holder['ticks'][0]['seconds']:.3f}s, "
                    f"{holder['ticks'][1]['seconds']:.3f}s, "
                    f"{holder['ticks'][2]['seconds']:.3f}s, "
                    f"total {timings['total']:.3f}s, all "
                    "inside budget")

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
        result["ticks"] = holder["ticks"]
        result["timings"] = holder["timings"]
        result["budgets"] = holder["budgets"]

    lines = ["INT-023 watchdog under load",
             f"room: {MESSAGE_COUNT} messages, queue: {JOB_COUNT} "
             f"jobs ({CLAIMED_COUNT} claimed: {SILENT_COUNT} "
             f"silent, {STUCK_COUNT} stuck, "
             f"{JOB_COUNT - CLAIMED_COUNT} open)",
             ("queue: in-memory fake surface, namespace "
              f"{integration.INT_JOBNS}, caps "
              f"{integration.INT_CAPNS}, room {integration.INT_ROOM}"),
             ("clock: fake clock advanced 61 minutes past the "
              "stall thresholds, claim leases, and presence "
              "TTL; tick 2 runs 5 minutes later, inside the "
              "30-minute dedupe cooldown; timings are "
              "perf_counter wall times"),
             ("alerts: template text (no Spark client passed "
              "to any tick); store records stay standing "
              "after tick 3 because tick silence is not "
              "WDG-014 resolution"),
             ""]
    for name, passed, detail in stages:
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    lines.append("")
    lines.append("INT-023: " + ("PASS (all stages)"
                                if ok else "FAIL"))
    transcript = "\n".join(lines) + "\n"
    result["transcript"] = transcript
    if ok:
        result["table"] = render_watchdog_load_md(result)
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
