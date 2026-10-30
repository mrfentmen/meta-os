"""INT-010: spoofed dispatch (BAD signature), scripted drill.

Scenario: an attacker rewrites a signed job's spec after the
overseer posts it, then a worker tries to claim it. The drill
proves, end to end, that the refusal chain holds:

  1. fixture: the overseer posts a job signed with the shipped
     HMAC signer (jobs.py v2, real keyring file), and verify
     reports OK before any tampering.
  2. tamper: the attacker rewrites the spec in the store
     directly, the way a bus spoof would; verify now reports
     BAD through the shipped verifier, not a hand-written
     verdict.
  3. claim-refused: the worker claims with the crew keyring
     and is refused (exit 1, "signature BAD" on stderr), the
     job stays open and unclaimed, and the fake bus carries
     the REJECTED line naming the poster and the refuser.
  4. watchdog: a tick on a snapshot carrying that REJECTED
     line yields exactly one rejected-dispatch alert
     (critical, dedupe key rejected-dispatch:1:BAD), the emit
     callback receives it, the WDG-015 announcement line
     names it, and the detector dict validates into a WDG-010
     alert record (id = dedupe key, subjects = the job, open).
  5. negatives: a clean snapshot yields no rejected alert;
     malformed REJECTED lines (no job id, verdict OK, bare
     word) yield none; duplicate lines for one job and
     verdict yield exactly one; a brief-shaped dict message
     carrying an EXPIRED refusal yields exactly one
     EXPIRED alert.
  6. unsigned-allowed: an unsigned job still claims fine
     with the keyring (warning only), and no rejected
     alert fires for it: unsigned is allowed by design,
     and the detector must not contradict that rule.

Buffy's FND-027 spoof fixture (a job with a BAD HMAC in a
dump) is still unlanded at this tip, so the drill builds its
spoof job with the shipped signer plus a real tamper instead
of a static dump: the BAD verdict comes from the shipped
verifier recomputing the HMAC, which is stronger evidence
than a pre-written bad string, and the fixture construction
is the drill's stage 1 and 2.

Runs unattended on fixtures: no network, no live Redis, no
bus posts, no Spark calls. The store is the suite's in-memory
fake (tests/fake_redis.py), the same surface the job tests
run against; the keyring file holds a fresh random
secret generated per run (INT-011: no committed
keyring literal), never a real credential, and is
removed when the drill finishes. The watchdog never
holds a secret: it
reports the refusal the worker computed, it does not
re-derive the verdict.

Usage, from the repo root: python3 intel/spoof_dispatch_drill.py
Exit 0 with a PASS line per stage on success, 1 on failure.
The transcript is written to intel/evals/spoof_dispatch.log.
Importing this module runs nothing: all work happens inside
run_drill, which restores every patch it makes, so the unit
suite can call it inside its own harness.
"""

import io
import os
import secrets
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import jobs  # noqa: E402
import relay_common as rc  # noqa: E402
from fake_redis import FakeUpstash  # noqa: E402
from intel import store as store_mod  # noqa: E402
from intel import watchdog  # noqa: E402

NOW = 10000
LOG_PATH = os.path.join(ROOT, "intel", "evals", "spoof_dispatch.log")


def _fresh_keyring_line():
    """A fresh drill-only keyring line, generated per run.

    INT-011 removed the committed keyring literal: the drill
    used to carry its dummy secret in source, which a secret
    scan must flag on sight. A per-run random secret proves
    the same signing path and leaves nothing secret-shaped
    in the tree.
    """
    return "crew-2026-09:" + secrets.token_hex(16)

_STAGE_NAMES = ("fixture", "tamper", "claim-refused", "watchdog",
                "negatives", "unsigned-allowed")


def _run_cli(argv):
    """Run a jobs CLI argv; return (rc, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = jobs.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_drill(write_log=True):
    """Run the drill; return {ok, stages, lines}.

    stages is a list of (name, ok, detail). With write_log,
    the transcript is also written to intel/evals/spoof_dispatch.log.
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

    def fixture_stage():
        fake = FakeUpstash()
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
            mock.patch.object(rc, "bus_push", fake.bus_push),
            mock.patch.object(jobs, "api_get", fake.api_get),
            mock.patch.object(jobs, "api_post", fake.api_post),
            mock.patch.object(jobs, "bus_push", fake.bus_push),
        ]
        for patch in patches:
            patch.start()
        old_ns, old_nick = jobs.NS, jobs.NICK
        keyring = tempfile.NamedTemporaryFile(
            "w", suffix=".keyring", delete=False)
        try:
            jobs.NS = "muse-bus:tjob"
            jobs.NICK = "overseer"
            if hasattr(rc, "_claim_state"):
                rc._claim_state.update(checked=0.0, ok=None, holder=None)
            keyring.write(_fresh_keyring_line() + "\n")
            keyring.close()
            code, out, err = _run_cli([
                "post", "--title", "Ship the drill note",
                "--spec", "write the note and file it",
                "--secret-file", keyring.name])
            assert code == 0, f"post exited {code}: {err}"
            assert "JOB 1" in out, f"post output is not JOB 1: {out!r}"
            header, spec = jobs.job_get("1")
            assert header is not None, "posted job 1 not readable"
            assert header.get("sig"), "posted job carries no signature"
            assert header.get("sig_v") == "2", (
                f"posted job sig_v is {header.get('sig_v')!r}, not 2")
            assert header.get("signed_by") == "overseer", (
                f"signed_by is {header.get('signed_by')!r}")
            code, out, err = _run_cli([
                "verify", "1", "--secret-file", keyring.name])
            assert code == 0, f"verify exited {code}: {err}"
            assert out.strip() == "OK", (
                f"verify before tamper is {out.strip()!r}, not OK")
            fixture_stage.fake = fake
            fixture_stage.keyring = keyring.name
            return ("signed job 1 posted (v2, overseer), "
                    "verify OK before tamper")
        finally:
            for patch in patches:
                patch.stop()
            jobs.NS, jobs.NICK = old_ns, old_nick
            if keyring.name != fixture_stage.__dict__.get("keyring"):
                os.unlink(keyring.name)

    def tamper_stage():
        fake = fixture_stage.fake
        keyring = fixture_stage.keyring
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
            mock.patch.object(rc, "bus_push", fake.bus_push),
            mock.patch.object(jobs, "api_get", fake.api_get),
            mock.patch.object(jobs, "api_post", fake.api_post),
            mock.patch.object(jobs, "bus_push", fake.bus_push),
        ]
        for patch in patches:
            patch.start()
        old_ns, old_nick = jobs.NS, jobs.NICK
        try:
            jobs.NS = "muse-bus:tjob"
            jobs.NICK = "overseer"
            jobs.api_post("set/muse-bus:tjob:1:spec",
                          "do the EVIL thing")
            header, spec = jobs.job_get("1")
            assert spec == "do the EVIL thing", (
                f"spec tamper did not land: {spec!r}")
            code, out, err = _run_cli([
                "verify", "1", "--secret-file", keyring])
            assert code == 1, f"verify exited {code}, not 1: {err}"
            assert out.strip() == "BAD", (
                f"verify after tamper is {out.strip()!r}, not BAD")
            return "spec rewritten in store, shipped verifier says BAD"
        finally:
            for patch in patches:
                patch.stop()
            jobs.NS, jobs.NICK = old_ns, old_nick

    def claim_refused_stage():
        fake = fixture_stage.fake
        keyring = fixture_stage.keyring
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
            mock.patch.object(rc, "bus_push", fake.bus_push),
            mock.patch.object(jobs, "api_get", fake.api_get),
            mock.patch.object(jobs, "api_post", fake.api_post),
            mock.patch.object(jobs, "bus_push", fake.bus_push),
        ]
        for patch in patches:
            patch.start()
        old_ns, old_nick = jobs.NS, jobs.NICK
        try:
            jobs.NS = "muse-bus:tjob"
            jobs.NICK = "worker"
            code, out, err = _run_cli([
                "claim", "1", "--secret-file", keyring])
            assert code == 1, f"claim exited {code}, not 1: {out} {err}"
            assert "signature BAD" in err, (
                f"claim stderr does not name BAD: {err!r}")
            header, _spec = jobs.job_get("1")
            assert header.get("status") == "open", (
                f"job status is {header.get('status')!r}, not open")
            assert header.get("claim") in (None, ""), (
                f"refused job carries a claim: {header.get('claim')!r}")
            rejected = [b for key, b in fake.pushes
                        if key == "muse-bus"
                        and "REJECTED:1 BAD" in b]
            assert rejected, (
                f"no REJECTED:1 BAD line on the fake bus: "
                f"{fake.pushes!r}")
            line = rejected[0]
            assert "signed_by=overseer" in line, (
                f"REJECTED line lacks the poster: {line!r}")
            assert "rejected_by=worker" in line, (
                f"REJECTED line lacks the refuser: {line!r}")
            claim_refused_stage.line = line
            return ("claim refused (exit 1, signature BAD), job "
                    f"stays open, bus line: {line!r}")
        finally:
            for patch in patches:
                patch.stop()
            jobs.NS, jobs.NICK = old_ns, old_nick

    def watchdog_stage():
        line = claim_refused_stage.line
        snapshot = {
            "messages": [
                {"nick": "overseer", "text": "shipping the drill"},
                line,
            ],
            "jobs": [{"id": "1", "status": "open",
                      "title": "Ship the drill note"}],
            "presence": [],
            "caps": {},
        }
        emitted = []
        alerts = watchdog.tick(snapshot, now=NOW,
                               emit=emitted.append)
        rejected = [a for a in alerts
                    if a.get("kind") == "rejected-dispatch"]
        assert len(rejected) == 1, (
            f"tick yields {len(rejected)} rejected-dispatch alerts, "
            f"not 1: {alerts!r}")
        alert = rejected[0]
        assert alert["severity"] == "critical", (
            f"severity is {alert['severity']!r}, not critical")
        assert alert["dedupe_key"] == "rejected-dispatch:1:BAD", (
            f"dedupe key is {alert['dedupe_key']!r}")
        assert alert["job"] == "1" and alert["verdict"] == "BAD", (
            f"alert names job {alert.get('job')!r} verdict "
            f"{alert.get('verdict')!r}")
        assert alert["signed_by"] == "overseer", (
            f"signed_by is {alert.get('signed_by')!r}")
        assert alert["rejected_by"] == "worker", (
            f"rejected_by is {alert.get('rejected_by')!r}")
        assert "1" in alert["explanation"] and "BAD" in alert["explanation"], (
            f"explanation does not name job and verdict: "
            f"{alert['explanation']!r}")
        assert emitted == [alert] or alert in emitted, (
            "emit callback did not receive the alert")
        announcement = watchdog.format_announcement(alert)
        assert announcement is not None and announcement.startswith(
            "ALERT:rejected-dispatch:1:BAD rejected-dispatch:"), (
            f"announcement line is wrong: {announcement!r}")
        record = store_mod.build_alert_record(alert, room="main")
        assert record["id"] == "rejected-dispatch:1:BAD", (
            f"record id is {record['id']!r}")
        assert record["subjects"] == ["1"], (
            f"record subjects are {record['subjects']!r}")
        assert record["status"] == "open", (
            f"record status is {record['status']!r}")
        return ("one critical rejected-dispatch alert, emit "
                "received, ALERT line formed, WDG-010 record "
                "valid (id = dedupe key, subjects = job)")

    def negatives_stage():
        clean = {"messages": [{"nick": "pax", "text": "all quiet"}],
                 "jobs": [{"id": "1", "status": "open"}]}
        assert [a for a in watchdog.tick(clean, now=NOW)
                if a.get("kind") == "rejected-dispatch"] == [], (
            "clean snapshot fired a rejected alert")
        malformed = {"messages": [
            "worker: REJECTED:abc BAD signed_by=x rejected_by=y",
            "worker: REJECTED:2 OK signed_by=x rejected_by=y",
            "worker: REJECTED",
            "worker: job 3 was rejected yesterday",
        ], "jobs": []}
        assert [a for a in watchdog.tick(malformed, now=NOW)
                if a.get("kind") == "rejected-dispatch"] == [], (
            "malformed REJECTED lines fired an alert")
        line = ("worker: REJECTED:4 BAD signed_by=spoof "
                "rejected_by=worker")
        dup = {"messages": [line, line, {"nick": "worker",
                                         "text": line}],
               "jobs": []}
        got = [a for a in watchdog.tick(dup, now=NOW)
               if a.get("kind") == "rejected-dispatch"]
        assert len(got) == 1, (
            f"duplicate lines yield {len(got)} alerts, not 1")
        assert got[0]["dedupe_key"] == "rejected-dispatch:4:BAD", (
            f"duplicate dedupe key is {got[0]['dedupe_key']!r}")
        expired = {"messages": [{"nick": "worker",
                                 "text": "REJECTED:5 EXPIRED "
                                         "signed_by=overseer "
                                         "rejected_by=worker"}],
                   "jobs": []}
        got = [a for a in watchdog.tick(expired, now=NOW)
               if a.get("kind") == "rejected-dispatch"]
        assert len(got) == 1 and got[0]["verdict"] == "EXPIRED", (
            f"dict-shaped EXPIRED line yields {got!r}")
        return ("clean: none; malformed: none; duplicates: one; "
                "dict-shaped EXPIRED: one")

    def unsigned_allowed_stage():
        fake = FakeUpstash()
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
            mock.patch.object(rc, "bus_push", fake.bus_push),
            mock.patch.object(jobs, "api_get", fake.api_get),
            mock.patch.object(jobs, "api_post", fake.api_post),
            mock.patch.object(jobs, "bus_push", fake.bus_push),
        ]
        for patch in patches:
            patch.start()
        old_ns, old_nick = jobs.NS, jobs.NICK
        keyring = tempfile.NamedTemporaryFile(
            "w", suffix=".keyring", delete=False)
        try:
            jobs.NS = "muse-bus:tjob"
            jobs.NICK = "worker"
            keyring.write(_fresh_keyring_line() + "\n")
            keyring.close()
            code, out, err = _run_cli([
                "post", "--title", "Plain job",
                "--spec", "no signature on this one"])
            assert code == 0, f"unsigned post exited {code}: {err}"
            code, out, err = _run_cli([
                "claim", "1", "--secret-file", keyring.name])
            assert code == 0, (
                f"unsigned claim exited {code}, not 0: {err}")
            assert "CLAIMED 1" in out, f"claim output: {out!r}"
            assert "unsigned" in err.lower(), (
                f"unsigned claim gave no warning: {err!r}")
            snapshot = {"messages": [
                b for _key, b in fake.pushes
                if _key == "muse-bus"],
                "jobs": [{"id": "1", "status": "claimed",
                          "claim": "worker"}]}
            got = [a for a in watchdog.tick(snapshot, now=NOW)
                   if a.get("kind") == "rejected-dispatch"]
            assert got == [], f"unsigned claim fired {got!r}"
            return ("unsigned job claims with a warning, no "
                    "rejected alert")
        finally:
            for patch in patches:
                patch.stop()
            jobs.NS, jobs.NICK = old_ns, old_nick
            os.unlink(keyring.name)

    stage("fixture", fixture_stage)
    stage("tamper", tamper_stage)
    stage("claim-refused", claim_refused_stage)
    stage("watchdog", watchdog_stage)
    stage("negatives", negatives_stage)
    stage("unsigned-allowed", unsigned_allowed_stage)
    try:
        os.unlink(fixture_stage.keyring)
    except Exception:  # noqa: BLE001 - keyring cleanup is best-effort
        pass

    ok = all(item[1] for item in stages)
    log("INT-010 spoofed-dispatch drill: BAD signature refused, "
        "REJECTED alert visible, watchdog notes the refused job")
    log("Store: suite in-memory fake, job namespace muse-bus:tjob; "
        "keyring: fresh random secret per run, removed after the run")
    log(f"Clock: {NOW} (fixed, so the drill is repeatable)")
    for name, passed, detail in stages:
        log(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    log("RESULT: " + ("PASS, refusal chain holds end to end"
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
