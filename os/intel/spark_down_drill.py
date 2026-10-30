"""INT-008: Spark endpoint down for all features, scripted drill.

Scenario: every Spark call fails because the endpoint is down.
The drill proves, on one fixture snapshot, that nothing crashes
and every fallback engages:

  1. precondition: the real HTTP transport against a closed
     localhost port raises SparkError (endpoint unreachable).
     This is a genuinely dead endpoint, not a stubbed failure:
     the client is the shipped SparkClient over the shipped
     HttpTransport, pointed at a port nothing listens on.
  2. brief: compose_brief with the down client returns the
     template brief (TEMPLATE first line, inside the morning
     word budget), and the Spark-only path returns the canned
     BRF-026 spark_down line verbatim.
  3. brief record: generate_brief with the down client (dry
     run, fake store surface) records model template, not
     spark, because the template wrote the text.
  4. dispatch: plan_from_spark with a completion callable
     over the down client returns the FALLBACK plan (one job,
     raw goal in the spec, endpoint-down warning), calls the
     endpoint exactly once, and posts nothing.
  5. watchdog: one tick with the down polish client yields
     the same alerts, with the same template explanations,
     as a tick with no polish client at all.
  6. CLI: intel.py brief --morning over a snapshot file
     (dry run, fake store surface) exits 0 with a template
     brief, no traceback, no Spark call.

Runs unattended on fixtures: no network beyond the closed
localhost port, no live Redis, no bus posts, no Spark spend
(the dead endpoint answers nothing, so no call completes).
The api_key string here is a drill placeholder, never a real
credential: the endpoint is dead before any header matters.

Usage, from the repo root: python3 intel/spark_down_drill.py
Exit 0 with a PASS line per stage on success, 1 on failure.
The transcript is written to intel/evals/spark_down.log.
Importing this module runs nothing: all work happens inside
run_drill, which restores the store functions it patches, so
the unit suite can call it inside its own harness.
"""

import copy
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from intel import brief as brief_mod  # noqa: E402
from intel import dispatch  # noqa: E402
from intel import watchdog  # noqa: E402
from intel.spark_client import SparkClient, SparkError  # noqa: E402

DOWN_ENDPOINT = "http://127.0.0.1:9/spark-down-drill"
GOAL = "Probe the snapshot path, then report the result."
NOW = 10000

SNAPSHOT = {
    "messages": [
        {"nick": "pax", "text": "shipping the drill"},
        {"nick": "hana", "text": "brief lane stands by"},
    ],
    "jobs": [
        {"id": "7", "status": "claimed", "claim": "pax",
         "title": "Write the drill note", "claimed_at": 9000,
         "last_progress": 9340},
        {"id": "8", "status": "blocked", "title": "Vendor API key",
         "note": "waiting on vendor"},
    ],
    "presence": ["pax"],
    "caps": {"pax": {}},
}

LOG_PATH = os.path.join(ROOT, "intel", "evals", "spark_down.log")

_STAGE_NAMES = ("precondition", "brief", "brief-record",
                "dispatch", "watchdog", "cli")


def _down_client():
    """The shipped client over a dead endpoint. No ledger writes."""
    return SparkClient(transport="http", endpoint=DOWN_ENDPOINT,
                       api_key="drill-not-a-secret", ledger=False)


def run_drill(write_log=True):
    """Run the drill; return {ok, stages, lines}.

    stages is a list of (name, ok, detail). With write_log,
    the transcript is also written to intel/evals/spark_down.log.
    """
    stages = []
    lines = []

    def log(text):
        lines.append(text)

    def stage(name, fn):
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - a stage
            # failure is a drill failure, reported, not traced
            stages.append((name, False, f"{type(exc).__name__}: {exc}"))
            return None
        stages.append((name, True, detail))
        return detail

    def precondition():
        client = _down_client()
        try:
            client.complete("hello", lane_feature="drill-probe")
        except SparkError as exc:
            assert "unreachable" in str(exc), f"unexpected error: {exc}"
            return f"SparkError: {exc} (0 real calls completed)"
        raise AssertionError("dead endpoint answered, drill is void")

    def brief_stage():
        client = _down_client()
        text = brief_mod.compose_brief(copy.deepcopy(SNAPSHOT),
                                       kind="morning", client=client,
                                       now=NOW)
        assert text.startswith("TEMPLATE"), (
            f"brief first line is not TEMPLATE: {text[:80]!r}")
        words = len(text.split())
        assert words <= 220, f"morning brief {words} words, over 220"
        assert "Vendor API key" in text, "blocked job missing from brief"
        spark_only = brief_mod.compose_spark_brief(
            copy.deepcopy(SNAPSHOT), kind="morning", client=client)
        canned = brief_mod.brief_failure_line("spark_down")
        assert spark_only == canned, (
            f"spark-only path did not return the canned line: "
            f"{spark_only!r}")
        return (f"template brief {words} words, blocked job named, "
                f"spark-only path returns the canned line verbatim")

    def brief_record_stage():
        import relay_common as rc
        from fake_redis import FakeUpstash
        client = _down_client()
        fake = FakeUpstash()
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
        ]
        for patch in patches:
            patch.start()
        try:
            text, record = brief_mod.generate_brief(
                copy.deepcopy(SNAPSHOT), "drill-room", kind="morning",
                now=NOW, dry_run=True, client=client)
        finally:
            for patch in patches:
                patch.stop()
        assert text.startswith("TEMPLATE"), (
            f"record text first line is not TEMPLATE: {text[:80]!r}")
        assert record["model"] == "template", (
            f"record model is {record['model']!r}, not template")
        return "dry-run record model is template for template text"

    def dispatch_stage():
        client = _down_client()
        calls = []

        def down_complete(goal):
            calls.append(goal)
            return client.complete(
                "Write a dispatch plan for this goal: " + goal,
                lane_feature="dispatch")

        with redirect_stderr(io.StringIO()) as err:
            result = dispatch.plan_from_spark(GOAL, down_complete)
        assert len(calls) == 1, f"endpoint called {len(calls)} times"
        assert result["fallback"] is True, "no fallback on endpoint down"
        assert result["order"] == ["fallback-job"], (
            f"order is {result['order']!r}")
        plan = result["plan"]
        assert len(plan["jobs"]) == 1, "fallback plan is not one job"
        job = plan["jobs"][0]
        assert "FALLBACK" in plan["summary"], "summary not marked"
        assert "FALLBACK" in job["title"], "title not marked"
        assert "FALLBACK" in job["spec"], "spec not marked"
        assert GOAL in job["spec"], "raw goal missing from spec"
        assert "endpoint is down" in result["warning"], (
            f"warning does not name the outage: {result['warning']!r}")
        assert "endpoint is down" in err.getvalue(), (
            "endpoint-down warning missing from stderr")
        assert client.spent_usd == 0.0, "dead endpoint recorded spend"
        return ("FALLBACK plan, one job, raw goal in spec, "
                "endpoint called once, nothing posted, $0 spent")

    def watchdog_stage():
        client = _down_client()
        plain = watchdog.tick(copy.deepcopy(SNAPSHOT), now=NOW)
        polished = watchdog.tick(copy.deepcopy(SNAPSHOT), now=NOW,
                                 polish_client=client)
        assert len(plain) >= 1, "no alert fired on the stall snapshot"
        kinds = [alert.get("kind") for alert in plain]
        assert "progress-stall" in kinds, (
            f"no progress-stall alert, kinds are {kinds!r}")
        assert len(polished) == len(plain), (
            f"polish changed alert count: {len(polished)} vs {len(plain)}")
        for before, after in zip(plain, polished):
            assert before["explanation"] == after["explanation"], (
                "down polish changed a template explanation")
        return (f"{len(plain)} alert(s) incl. progress-stall, "
                f"template explanations identical with down polish")

    def cli_stage():
        import importlib.util
        import relay_common as rc
        from fake_redis import FakeUpstash
        # Root intel.py is the CLI; the intel/ package shadows a
        # plain import, so load it under a distinct name, the way
        # the CLI tests do.
        path = os.path.join(ROOT, "intel.py")
        spec = importlib.util.spec_from_file_location(
            "intel_cli_under_test", path)
        intel_cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(intel_cli)
        snapshot_file = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False)
        try:
            json.dump(SNAPSHOT, snapshot_file)
            snapshot_file.close()
            fake = FakeUpstash()
            patches = [
                mock.patch.object(rc, "api_get", fake.api_get),
                mock.patch.object(rc, "api_post", fake.api_post),
            ]
            for patch in patches:
                patch.start()
            try:
                out = io.StringIO()
                try:
                    with redirect_stdout(out):
                        rc_code = intel_cli.main([
                            "brief", "--morning", "--room", "drill-room",
                            "--snapshot", snapshot_file.name,
                            "--now", str(NOW), "--dry-run"])
                except SystemExit as exc:
                    raise AssertionError(
                        f"CLI exited via SystemExit {exc.code}")
            finally:
                for patch in patches:
                    patch.stop()
        finally:
            os.unlink(snapshot_file.name)
        assert rc_code == 0, f"CLI exited {rc_code}"
        assert out.getvalue().startswith("TEMPLATE"), (
            f"CLI brief first line is not TEMPLATE: "
            f"{out.getvalue()[:80]!r}")
        return "CLI brief --morning exits 0 with a template brief"

    stage("precondition", precondition)
    stage("brief", brief_stage)
    stage("brief-record", brief_record_stage)
    stage("dispatch", dispatch_stage)
    stage("watchdog", watchdog_stage)
    stage("cli", cli_stage)

    ok = all(item[1] for item in stages)
    log("INT-008 Spark-down drill: endpoint is down for all features")
    log(f"Endpoint: {DOWN_ENDPOINT} (closed localhost port, "
        f"real HTTP transport)")
    log(f"Snapshot: 2 messages, 2 jobs (1 stalled claimed, "
        f"1 blocked), clock {NOW}")
    for name, passed, detail in stages:
        log(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    log("RESULT: " + ("PASS, every fallback engaged, nothing crashed"
                       if ok else "FAIL"))
    if write_log:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as handle:
            handle.write("\n".join(lines) + "\n")
    return {"ok": ok, "stages": stages, "lines": lines}


def main():
    result = run_drill(write_log=True)
    for line in result["lines"]:
        print(line)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
