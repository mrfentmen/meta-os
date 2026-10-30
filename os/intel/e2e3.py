"""intel/e2e3.py -- INT-004 end-to-end test 3, scripted loop.

A fresh nick joins a room where a drill is already running, and
the on-join brief it is offered names the drill's blocked item
and the drill's active alert, as one scripted run with a
transcript written to intel/evals/e2e3.log.

What this run is, plainly:

- The queue is the in-memory fake Redis surface from
  tests/fake_redis.py, the same surface the unit suite uses.
  Nothing here touches the live bus or posts a real job. The job
  namespace is the INT-001 integration namespace
  (muse-bus:int-job), the capability namespace is
  muse-bus:int-cap, and the room is build-int, so even the fake
  state is disjoint from production keys.
- Every queue transition is a real jobs.py command: post,
  claim, progress, blocked. The watchdog step reads a real
  intel/ingest.py snapshot of that queue state, not a
  hand-built dict. The alert is stored through the real
  intel/store.py write_alert path, so the brief reads the
  stored WDG-010 record, not the raw detector dict.
- The on-join path is the BRF-029 path, not a shortcut: the
  fresh nick beats presence, detect_new_nicks names it as
  new (it authored no room message), offer_onjoin_brief
  returns an offer record with no brief attached, and only
  then does generate_brief(kind="onjoin") write the brief.
  The offer is the whole effect until invoked: no brief
  exists before the invocation, and the loop asserts that.
- The brief is a template brief (client None), not a Spark
  brief: GOV-001 leaves live Spark transport blocked, so the
  template path is the honest path here, and the transcript
  says TEMPLATE on its first line. The loop proves the
  on-join content path, not the Spark composer.
- Time travel is the one simulation, and it uses the fake's
  own injectable clock: time.time is patched to the fake
  clock and the fake is advanced, so presence TTL (120s)
  lapses by the fake's real expiry rule. Nothing else
  about the drill is faked.
- Two gaps this loop names instead of hiding. First, the
  brief's Blocked section names the blocked job's id and
  title, but not its reason verbatim: real snapshot rows
  carry no note field, so extract_blocked sees an empty
  reason on a real snapshot. The loop asserts id and title
  only, and the reason gap is recorded here and in the
  README section, not papered over by hand-editing the
  snapshot. Second, the loop attaches the stored alert
  record to the brief snapshot itself: ingest snapshots
  carry no alerts section, so the glue from tick to brief
  is the caller passing the stored records in, exactly as
  the dashboard and CLI do. The INT-004 fix in this batch
  is the other side of that glue: extract_watch_items used
  to read only a summary field, while stored WDG-010
  records carry explanation instead, so a brief built from
  stored records named each alert id with nothing after
  it. The extractor now falls back to the explanation's
  first line, and the loop pins that behavior.
- The alert announcement line is held, never posted, and
  the brief generation posts nothing to the room either:
  the loop asserts the room message list gains no ALERT
  line and does not grow at all across the brief step.

Stages, each asserted, any failure failing the run:

  1. drill setup: two jobs posted, both open.
  2. blocked item: worker-b claims the release job and
     marks it blocked with a reason; the snapshot carries
     the job blocked and the BLOCKED announcement.
  3. stall and alert: worker-a claims and progresses the
     stall job, a healthy tick yields zero alerts, then
     after the stall window passes on the fake clock a
     tick yields exactly one presence-stall alert, which
     is stored and reads back by id; the announcement
     line is held.
  4. fresh nick joins: a nick with no prior message beats
     presence, detect_new_nicks names exactly that nick,
     and the offer record carries no brief yet.
  5. on-join brief: the generated onjoin brief is a
     template brief within its 150-word budget, its
     Blocked section names the blocked job id and title,
     its Watch items section names the stored alert id
     and the alert explanation's first line, and the
     brief is stored and retrievable by id.
  6. no auto-post: the room message list is unchanged by
     the brief step and holds no ALERT line.

Usage, from the repo root: python3 intel/e2e3.py
Exit 0 with the transcript on stdout and in
intel/evals/e2e3.log when every stage passes, exit 1
otherwise. Importing this module runs nothing: all setup
(env, fake surface, nicks, clock) happens inside run_loop,
and run_loop restores the job namespace, capability
namespace, and nicks it changed, so the unit suite can call
it inside its own harness.
"""

import contextlib
import io
import json
import os
import sys
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from intel import integration  # noqa: E402

BLOCKED_TITLE = "Ship the e2e3 release note"
BLOCKED_SPEC = ("Goal: ship the INT-004 release note. Context: "
                "INT-004 fixture. Files: intel/e2e3_release.txt. "
                "Steps: write the note. "
                "Out of scope: any other file.")
BLOCKED_FILES = "intel/e2e3_release.txt"
BLOCKED_REASON = "waiting on the outside review, no reply yet"
STALL_TITLE = "Fix the e2e3 stall note"
STALL_SPEC = ("Goal: close the INT-004 loop. Context: INT-004 fixture. "
              "Files: intel/e2e3_note.txt. Steps: write the note. "
              "Out of scope: any other file.")
STALL_FILES = "intel/e2e3_note.txt"
MAX_ATTEMPTS = 3
WORKER_A = "worker-a"
WORKER_B = "worker-b"
STALL_PROGRESS = "halfway through the stall note"
FRESH_NICK = "newbie"

LOG_PATH = os.path.join(ROOT, "intel", "evals", "e2e3.log")

_STAGE_NAMES = ("drill setup", "blocked item", "stall and alert",
                "fresh nick joins", "on-join brief", "no auto-post")


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


def _section_lines(text, heading):
    """Lines of one brief section, between its heading and the next."""
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index] in ("Decisions", "In flight", "Owners",
                            "Blocked and why", "Watch items"):
            end = index
            break
    return [line for line in lines[start:end] if line.strip()]


def run_loop(write_log=True):
    """Run the INT-004 loop; return the result dict.

    Returns {"ok": bool, "stages": [(name, ok, detail)], ...}.
    With write_log, the transcript is also written to
    intel/evals/e2e3.log. Restores jobs.NS, capabilities.CAPNS,
    and the nicks it changed, so a caller inside another
    harness is unaffected.
    """
    # INT-001 import-order rule: the namespace variables must be
    # set before jobs (and mos.capabilities) are imported, or
    # the already-read prefixes do not move.
    integration.apply_env()
    import relay_common as rc  # noqa: E402
    import jobs  # noqa: E402
    from intel import brief  # noqa: E402
    from intel import ingest  # noqa: E402
    from intel import store  # noqa: E402
    from intel import thresholds  # noqa: E402
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

        job_holder = {}
        alert_holder = {}
        brief_holder = {}

        def do_setup():
            rc.NICK = "pax"
            jobs.NICK = "pax"
            before = _job_list_json(jobs)
            assert before == [], f"job list not empty before: {before}"
            posted = {}
            for key, title, spec, files in (
                    ("blocked", BLOCKED_TITLE, BLOCKED_SPEC,
                     BLOCKED_FILES),
                    ("stall", STALL_TITLE, STALL_SPEC, STALL_FILES)):
                code, out, err = _run_cli(jobs.main, [
                    "post", "--title", title, "--spec", spec,
                    "--files", files,
                    "--max-attempts", str(MAX_ATTEMPTS),
                    "--room", integration.INT_ROOM])
                assert code == 0, f"post failed: {err}"
                assert out.startswith("JOB "), \
                    f"unexpected post out: {out}"
                posted[key] = out.split()[1]
            listed = _job_list_json(jobs)
            assert len(listed) == 2, f"job list after posts: {listed}"
            rows = {job["id"]: job for job in listed}
            for key, job_id in posted.items():
                assert rows[job_id]["status"] == "open", rows[job_id]
            job_holder.update(posted)
            return (f"jobs {posted['blocked']} (release note) and "
                    f"{posted['stall']} (stall note) posted, both open")

        stage("drill setup", do_setup)

        def do_blocked():
            blocked_id = job_holder["blocked"]
            assert capabilities.register(WORKER_B, ["python"]) is True
            rc.NICK = WORKER_B
            jobs.NICK = WORKER_B
            code, _out, err = _run_cli(jobs.main, ["claim", blocked_id])
            assert code == 0, f"worker-b claim failed: {err}"
            code, out, err = _run_cli(
                jobs.main, ["blocked", blocked_id,
                            "--reason", BLOCKED_REASON])
            assert code == 0, f"worker-b blocked failed: {err}"
            assert out.startswith("BLOCKED "), \
                f"unexpected blocked out: {out}"
            listed = _job_list_json(jobs)
            row = {job["id"]: job for job in listed}[blocked_id]
            assert row["status"] == "blocked", f"job after blocked: {row}"
            assert row["claim"] is None, f"claim not released: {row}"
            snapshot = ingest.snapshot(integration.INT_ROOM)
            rows = {job["id"]: job for job in snapshot["jobs"]}
            assert rows[blocked_id]["status"] == "blocked"
            assert any(f"BLOCKED:{blocked_id} {BLOCKED_REASON}" in msg
                       for msg in snapshot["messages"]), (
                "BLOCKED announcement missing from room messages")
            return (f"job {blocked_id} blocked by {WORKER_B}, claim "
                    f"released, BLOCKED announcement on the room list")

        stage("blocked item", do_blocked)

        def do_stall_and_alert():
            stall_id = job_holder["stall"]
            assert capabilities.register(WORKER_A, ["python"]) is True
            rc.NICK = WORKER_A
            jobs.NICK = WORKER_A
            rc.presence_beat()
            code, _out, err = _run_cli(jobs.main, ["claim", stall_id])
            assert code == 0, f"worker-a claim failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["progress", stall_id, "--note", STALL_PROGRESS])
            assert code == 0, f"worker-a progress failed: {err}"
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert WORKER_A in snapshot["presence"], (
                "worker-a must be present while alive")
            rows = {job["id"]: job for job in snapshot["jobs"]}
            assert rows[stall_id]["status"] == "claimed"
            assert rows[stall_id]["claim"] == WORKER_A
            job_holder["last_progress_at"] = rows[stall_id][
                "last_progress_at"]
            got = watchdog.tick(snapshot, now=int(fake.now()))
            assert got == [], (
                f"healthy worker must yield zero alerts, got {got}")
            fake.advance(thresholds.STALL_MINUTES * 60 + 61)
            stall_now = int(fake.now())
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert WORKER_A not in snapshot["presence"], (
                "dead worker must be gone from presence")
            rows = {job["id"]: job for job in snapshot["jobs"]}
            assert rows[stall_id]["status"] == "claimed", (
                "job must still be claimed before any sweep")
            got = watchdog.tick(snapshot, now=stall_now)
            assert len(got) == 1, (
                f"dead worker must yield exactly one alert, got {len(got)}: {got}")
            alert = got[0]
            assert alert["kind"] == "presence-stall", alert
            assert alert["nick"] == WORKER_A, alert
            assert alert["job"] == stall_id, alert
            expected_age = stall_now - job_holder["last_progress_at"]
            assert alert["last_progress_age_seconds"] == expected_age, alert
            record = store.write_alert(alert, room=integration.INT_ROOM)
            assert record["id"] == alert["dedupe_key"], record
            reread = store.get_alert(record["id"])
            assert reread is not None and reread["id"] == record["id"], (
                "stored alert must read back by id")
            assert reread["status"] == "open", reread
            lines = watchdog.announcements_for(got)
            assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
            assert all(lines[0] not in msg
                       for msg in snapshot["messages"]), (
                "announcement line must be held, never posted")
            alert_holder["alert"] = alert
            alert_holder["record"] = record
            return (f"presence-stall alert for {WORKER_A}/{stall_id} "
                    f"stored as {record['id']}, age {expected_age}s; "
                    f"announcement line held")

        stage("stall and alert", do_stall_and_alert)

        def do_fresh_nick():
            rc.NICK = FRESH_NICK
            jobs.NICK = FRESH_NICK
            rc.presence_beat()
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert snapshot["presence"] == [FRESH_NICK], (
                f"presence must hold only the fresh nick, got "
                f"{snapshot['presence']}")
            new_nicks = brief.detect_new_nicks(snapshot)
            assert new_nicks == [FRESH_NICK], (
                f"fresh nick must be the only new nick, got {new_nicks}")
            offers = brief.offer_onjoin_brief(
                snapshot, integration.INT_ROOM, now=int(fake.now()))
            assert len(offers) == 1, f"offers must be exactly one: {offers}"
            offer = offers[0]
            assert offer["nick"] == FRESH_NICK, offer
            assert offer["kind"] == "onjoin", offer
            assert offer["status"] == "offered", offer
            assert offer["brief_generated"] is False, offer
            assert offer["brief_id"] is None, offer
            assert brief.list_briefs(integration.INT_ROOM) == [], (
                "no brief may exist before the offer is invoked")
            job_holder["messages_before_brief"] = len(snapshot["messages"])
            return (f"{FRESH_NICK} joined, offered an onjoin brief, "
                    f"none generated yet")

        stage("fresh nick joins", do_fresh_nick)

        def do_onjoin_brief():
            blocked_id = job_holder["blocked"]
            record = alert_holder["record"]
            snapshot = ingest.snapshot(integration.INT_ROOM)
            snapshot["alerts"] = [record]
            text, stored = brief.generate_brief(
                snapshot, integration.INT_ROOM, kind="onjoin",
                now=int(fake.now()))
            assert text.startswith("TEMPLATE"), (
                "onjoin brief here must be a template brief")
            words = len(text.split())
            assert words <= brief.BRIEF_BUDGETS["onjoin"], (
                f"onjoin brief over budget: {words} words")
            blocked_lines = _section_lines(text, "Blocked and why")
            assert any(blocked_id in line and BLOCKED_TITLE in line
                       for line in blocked_lines), (
                f"Blocked section must name job {blocked_id} "
                f"{BLOCKED_TITLE!r}, got: {blocked_lines}")
            watch_lines = _section_lines(text, "Watch items")
            explanation_first = record["explanation"].splitlines()[0].strip()
            assert any(record["id"] in line
                       and explanation_first in line
                       for line in watch_lines), (
                f"Watch items must name alert {record['id']} with "
                f"its explanation, got: {watch_lines}")
            assert stored["kind"] == "onjoin", stored
            entries = brief.list_briefs(integration.INT_ROOM)
            assert len(entries) == 1, f"brief index must hold one: {entries}"
            assert entries[0]["kind"] == "onjoin", entries
            fetched = brief.get_brief(integration.INT_ROOM,
                                      entries[0]["ts"])
            assert fetched is not None, "stored brief must read back"
            assert fetched["kind"] == "onjoin", fetched
            assert fetched["text"] == text, (
                "stored brief text must match the generated text")
            brief_holder["text"] = text
            return (f"onjoin brief ({words} words) names blocked job "
                    f"{blocked_id} and alert {record['id']}, stored "
                    f"and retrievable")

        stage("on-join brief", do_onjoin_brief)

        def do_no_auto_post():
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert len(snapshot["messages"]) == \
                job_holder["messages_before_brief"], (
                "brief step must not add room messages")
            assert not any("ALERT:" in msg
                           for msg in snapshot["messages"]), (
                "room messages must hold no ALERT line")
            return ("room message list unchanged across the brief "
                    "step, no ALERT line posted")

        stage("no auto-post", do_no_auto_post)
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
        result["blocked_job_id"] = job_holder["blocked"]
        result["stall_job_id"] = job_holder["stall"]
        result["alert"] = alert_holder["alert"]
        result["alert_record_id"] = alert_holder["record"]["id"]
        result["brief_text"] = brief_holder["text"]

    lines = ["INT-004 end-to-end test 3",
             f"blocked job: {BLOCKED_TITLE} (files: {BLOCKED_FILES})",
             f"stall job: {STALL_TITLE} (files: {STALL_FILES})",
             ("queue: in-memory fake surface, namespace "
              f"{integration.INT_JOBNS}, caps "
              f"{integration.INT_CAPNS}, room {integration.INT_ROOM}"),
             ("clock: fake clock advanced, never wall-waited; "
              "presence TTL 120s, stall window "
              f"{thresholds.STALL_MINUTES} minutes"),
             ("brief: template path (no live Spark call; GOV-001 "
              "leaves live transport blocked); fresh nick "
              f"{FRESH_NICK}"),
             ""]
    for name, passed, detail in stages:
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    lines.append("")
    lines.append("On-join brief text:")
    if "text" in brief_holder:
        lines.append(brief_holder["text"].rstrip())
    lines.append("")
    lines.append("INT-004: " + ("PASS (all stages)"
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
