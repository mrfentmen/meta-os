"""INT-009: Redis outage for all intel commands, scripted drill.

Scenario: the relay store is unreachable because the Redis
endpoint is down. The drill proves, by running the real CLI
against a genuinely dead endpoint, that every Redis-dependent
intel command fails loudly with RELAY_ERROR and exit 2, never
a traceback to the user, and that the commands that need no
store still succeed:

  1. precondition: the shipped relay_common.api_get against a
     closed localhost port raises RuntimeError (curl rc=7,
     connection refused, after 4 attempts). This is a genuinely
     dead endpoint, not a stubbed failure: the CLI under test
     is the shipped intel.py, pointed at a port nothing
     listens on.
  2. snapshot: exit 2, RELAY_ERROR, empty stdout, no
     Traceback (already clean before INT-009).
  3. brief --morning (store path): exit 2, RELAY_ERROR, no
     Traceback (INT-009 fix: the generation block used to let
     the store failure escape as a traceback).
  4. brief --morning --dry-run: exit 0 with a TEMPLATE brief.
     The BRF-028 guard fails open on a dead store, and a dry
     run stores nothing, so a dry-run brief is store-free in
     effect. Exiting 0 here is correct, not a gap.
  5. brief --list: exit 2, RELAY_ERROR, no Traceback
     (INT-009 fix).
  6. brief --show: exit 2, RELAY_ERROR, no Traceback
     (INT-009 fix).
  7. dispatch --show: exit 2, RELAY_ERROR, no Traceback
     (INT-009 fix).
  8. dispatch --undo: exit 2, RELAY_ERROR, no Traceback
     (INT-009 fix).
  9. dispatch posting (--approve, demo plan): exit 2,
     RELAY_ERROR, no Traceback, and stderr names that no
     dispatch record was stored (already clean before
     INT-009: jobs.py reports the failed post, post_plan
     raises PostError, the CLI surfaces it).
  10. dispatch --dry-run: exit 0, the plan renders. Dry-run
      validation is pure functions on the plan text (DSP-006)
      and never touches the store, so it stays up during an
      outage. Exiting 0 here is correct, not a gap.
  11. alerts --show: exit 2, RELAY_ERROR, no Traceback
      (already clean before INT-009).
  12. alerts query (--room --since): exit 2, RELAY_ERROR, no
      Traceback (already clean before INT-009).
  13. watch: exit 2, RELAY_ERROR UNIMPLEMENTED. The watch
      route is still the unimplemented stub (FND-016), so its
      failure is pre-existing, not Redis-caused; the drill
      records that distinction instead of claiming a Redis
      failure it cannot show.
  14. watchdog engine: tick on the stall snapshot still
      returns the progress-stall alert with no store wired in
      (detection is pure), while emit through
      intel.store.write_alert raises RuntimeError, caught by
      the drill, proving the write path fails loudly at the
      engine boundary instead of silently dropping alerts.

Runs unattended on fixtures: no network beyond the closed
localhost port, no live Redis, no bus posts, no Spark calls.
The token file the drill creates holds a dummy string, never
a real credential: the endpoint is dead before any header
matters, and the file is removed when the drill finishes.
Each Redis-touching stage waits out the shipped retry loop
(4 curl attempts), so the full drill takes about a minute.

Usage, from the repo root: python3 intel/redis_down_drill.py
Exit 0 with a PASS line per stage on success, 1 on failure.
The transcript is written to intel/evals/redis_down.log.
Importing this module runs nothing: all work happens inside
run_drill, which restores nothing it patches because the CLI
runs in subprocesses, so the unit suite can import it freely.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import store as store_mod  # noqa: E402
from intel import watchdog  # noqa: E402

DOWN_URL = "http://127.0.0.1:9"
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

LOG_PATH = os.path.join(ROOT, "intel", "evals", "redis_down.log")

_STAGE_NAMES = ("precondition", "snapshot", "brief-store",
                "brief-dry-run", "brief-list", "brief-show",
                "dispatch-show", "dispatch-undo",
                "dispatch-posting", "dispatch-dry-run",
                "alerts-show", "alerts-query", "watch",
                "watchdog-engine")


def _cli_env(token_file):
    """Subprocess env with the store pointed at the dead port."""
    env = dict(os.environ)
    env["MUSE_RELAY_URL"] = DOWN_URL
    env["MUSE_RELAY_TOKEN_FILE"] = token_file
    return env


def _run_cli(argv, env):
    """Run the real intel.py CLI; return (code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "intel.py"), *argv],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
        env=env)
    return proc.returncode, proc.stdout, proc.stderr


def _expect_loud_failure(argv, env, must_name=None):
    """A Redis-dependent command: exit 2, RELAY_ERROR, no trace."""
    code, out, err = _run_cli(argv, env)
    assert code == 2, f"{argv} exited {code}, not 2: {out!r} {err!r}"
    assert "RELAY_ERROR" in err, f"{argv} stderr lacks RELAY_ERROR: {err!r}"
    assert "Traceback" not in err, f"{argv} printed a traceback: {err!r}"
    assert out == "", f"{argv} printed stdout on failure: {out!r}"
    if must_name is not None:
        assert must_name in err, (
            f"{argv} stderr lacks {must_name!r}: {err!r}")
    return f"exit 2, RELAY_ERROR, no traceback, empty stdout"


def run_drill(write_log=True):
    """Run the drill; return {ok, stages, lines}.

    stages is a list of (name, ok, detail). With write_log,
    the transcript is also written to intel/evals/redis_down.log.
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

    token_dir = tempfile.mkdtemp(prefix="redis-down-drill-")
    token_file = os.path.join(token_dir, "token")
    with open(token_file, "w") as handle:
        handle.write("drill-dummy-token-not-a-secret")
    env = _cli_env(token_file)
    plan_path = os.path.join(ROOT, "hackathon", "demo_goal_plan.json")

    def precondition():
        import relay_common as rc
        # relay_common reads its URL and token file at import time,
        # so point this process at the same dead endpoint the CLI
        # subprocesses get through the environment, then restore.
        saved_url, saved_token_file = rc.RELAY_URL, rc.TOKEN_FILE
        rc.RELAY_URL, rc.TOKEN_FILE = DOWN_URL, token_file
        try:
            rc.api_get("lrange/muse-bus/0/0")
        except RuntimeError as exc:
            assert "request failed after 4 attempts" in str(exc), (
                f"unexpected error: {exc}")
            assert "curl rc=7" in str(exc), (
                f"not a connection-refused failure: {exc}")
            return f"RuntimeError: {exc} (real curl failure, dead port)"
        except Exception:
            raise
        finally:
            rc.RELAY_URL, rc.TOKEN_FILE = saved_url, saved_token_file
        raise AssertionError("dead endpoint answered, drill is void")

    def snapshot_stage():
        return _expect_loud_failure(
            ["snapshot", "--room", "drill-room"], env)

    def brief_store_stage():
        return _expect_loud_failure(
            ["brief", "--morning", "--room", "drill-room"], env)

    def brief_dry_run_stage():
        code, out, err = _run_cli(
            ["brief", "--morning", "--room", "drill-room",
             "--now", str(NOW), "--dry-run"], env)
        assert code == 0, f"dry-run brief exited {code}: {out!r} {err!r}"
        assert out.startswith("TEMPLATE"), (
            f"dry-run brief first line is not TEMPLATE: {out[:80]!r}")
        assert "Traceback" not in err, f"dry-run brief traced: {err!r}"
        return "exit 0, TEMPLATE brief, store-free by dry run"

    def brief_list_stage():
        return _expect_loud_failure(
            ["brief", "--list", "--room", "drill-room"], env)

    def brief_show_stage():
        return _expect_loud_failure(
            ["brief", "--show", "--room", "drill-room",
             "--ts", str(NOW)], env)

    def dispatch_show_stage():
        return _expect_loud_failure(
            ["dispatch", "--show", "drill-missing"], env)

    def dispatch_undo_stage():
        return _expect_loud_failure(
            ["dispatch", "--undo", "drill-missing"], env)

    def dispatch_posting_stage():
        return _expect_loud_failure(
            ["dispatch", "--goal", "drill goal", "--plan", plan_path,
             "--approve"], env, must_name="no dispatch record stored")

    def dispatch_dry_run_stage():
        code, out, err = _run_cli(
            ["dispatch", "--goal", "drill goal", "--dry-run",
             "--plan", plan_path], env)
        assert code == 0, f"dry-run exited {code}: {out!r} {err!r}"
        assert "jobs in posting order" in out, (
            f"dry-run did not render the plan: {out[:200]!r}")
        assert "Traceback" not in err, f"dry-run traced: {err!r}"
        return "exit 0, plan renders, pure validation, no store touch"

    def alerts_show_stage():
        return _expect_loud_failure(
            ["alerts", "--show", "--id", "drill-missing"], env)

    def alerts_query_stage():
        return _expect_loud_failure(
            ["alerts", "--show", "--room", "drill-room",
             "--since", str(NOW)], env)

    def watch_stage():
        code, out, err = _run_cli(["watch"], env)
        assert code == 2, f"watch exited {code}, not 2"
        assert "RELAY_ERROR" in err and "UNIMPLEMENTED" in err, (
            f"watch did not report the stub: {err!r}")
        assert out == "", f"watch printed stdout: {out!r}"
        return ("exit 2, RELAY_ERROR UNIMPLEMENTED: pre-existing stub, "
                "not a Redis failure")

    def watchdog_engine_stage():
        import relay_common as rc
        found = watchdog.tick(copy.deepcopy(SNAPSHOT), now=NOW)
        kinds = [alert.get("kind") for alert in found]
        assert "progress-stall" in kinds, (
            f"no progress-stall alert, kinds are {kinds!r}")
        # Same in-process config patch as the precondition: the
        # drill process itself has no MUSE_RELAY_URL, so without
        # it the write would fail on missing config, not on the
        # dead endpoint, and prove nothing about the outage.
        saved_url, saved_token_file = rc.RELAY_URL, rc.TOKEN_FILE
        rc.RELAY_URL, rc.TOKEN_FILE = DOWN_URL, token_file
        try:
            store_mod.write_alert(found[0], room="drill-room", now=NOW)
        except RuntimeError as exc:
            assert "attempts" in str(exc), f"unexpected error: {exc}"
            return (f"tick pure: {len(found)} alert(s) incl. "
                    f"progress-stall with no store; write_alert raises "
                    f"RuntimeError, caught, not silent")
        finally:
            rc.RELAY_URL, rc.TOKEN_FILE = saved_url, saved_token_file
        raise AssertionError("dead store accepted the alert write")

    stage("precondition", precondition)
    stage("snapshot", snapshot_stage)
    stage("brief-store", brief_store_stage)
    stage("brief-dry-run", brief_dry_run_stage)
    stage("brief-list", brief_list_stage)
    stage("brief-show", brief_show_stage)
    stage("dispatch-show", dispatch_show_stage)
    stage("dispatch-undo", dispatch_undo_stage)
    stage("dispatch-posting", dispatch_posting_stage)
    stage("dispatch-dry-run", dispatch_dry_run_stage)
    stage("alerts-show", alerts_show_stage)
    stage("alerts-query", alerts_query_stage)
    stage("watch", watch_stage)
    stage("watchdog-engine", watchdog_engine_stage)

    try:
        os.unlink(token_file)
        os.rmdir(token_dir)
    except OSError:
        pass

    ok = all(passed for _name, passed, _detail in stages)
    for name, passed, detail in stages:
        log(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    log(f"drill {'PASSED' if ok else 'FAILED'}: "
        f"{sum(1 for _n, p, _d in stages if p)}/{len(stages)} stages")
    if write_log:
        with open(LOG_PATH, "w") as handle:
            handle.write("\n".join(lines) + "\n")
    return {"ok": ok, "stages": stages, "lines": lines}


if __name__ == "__main__":
    result = run_drill()
    for line in result["lines"]:
        print(line)
    raise SystemExit(0 if result["ok"] else 1)
