"""Watchman subprocess-runner drill (Milo lane, OS-122 follow-up).

run_cycle() judged runs that were already collected, and
watchman_cycle.py proved the collection judgment on
fixture callables. This drill proves the missing half:
intel/watchman_runner.py actually runs the real Pax
OS-118 program, os/watchman/relay_watchman.py --once,
once per machine, and folds the results through
run_cycle() unchanged. Six checks:

1. The real --once run rings: snapshot files for one
   machine carry an open job addressed to a sleeping
   local agent, and the runner returns (True, stdout)
   with exactly one wake event naming the job and the
   agent. A second run over the same state file prints
   nothing: the watchman's own rung dedupe holds, and
   the run still counts as success.
2. The full cycle wires through: run_cycle_with_subprocess
   over a ringing machine and a quiet machine (empty
   snapshots) yields a fresh record for the ringer with
   a bell and no invented bell for the quiet machine,
   an empty journal, and clean diagnostics with no run
   failures.
3. A hanging watchman is a failed run, not a hung loop:
   a fake program that sleeps is killed at the timeout
   and run_once() reports ("timeout"), and the runner
   pair is (False, "").
4. A nonzero exit discards its stdout: a fake program
   that prints a line and exits 3 yields detail
   "exit-3" and an empty stdout, so partial lines never
   reach the loop as if they were events.
5. A missing program and bad inputs are contained: a
   nonexistent executable yields "not-found", an empty
   argv yields "bad-argv", a non-string machine and a
   raising command_for both yield (False, "") from the
   runner, and nothing raises.
6. A failed run ages honestly through the cycle: a
   machine whose runner now fails, with a prior record
   carrying a bell, comes back as a carried record with
   the bell unchanged, and the priors and journal the
   caller passed in come back unchanged.

What this drill does NOT claim, stated plainly. The
runner proves the local collection half, not a live
service: no booted test image, no relay-watchman.service
actually running (the runs here are one-shot --once
calls from a temp snapshot directory, not the unit),
no systemd restart of a dead watchman, no agent session
started (OS-119), no job reassigned (OS-125), no push
sent (Hana OS-097), and no live queue reader (OS-118's
snapshot files are still the interface until it lands;
the snapshots here are hand-written fixtures). A failed
run here is a diagnostics line, and the escalation is a
payload, never a send. No bus post, no live Redis, no
network.

Runs unattended: python3 intel/drills/watchman_runner.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import copy
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import watchman_runner as runner  # noqa: E402

NOW = 1000000


def _fail(message):
    print("FAIL: %s" % message)
    return 1


def _write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def _write_script(directory, name, body):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)
    return path


def _snapshots(directory, machine, jobs, agents):
    _write_json(os.path.join(
        directory, "watchman-jobs-%s.json" % machine), jobs)
    _write_json(os.path.join(
        directory, "watchman-agents-%s.json" % machine), agents)


def main():
    tmp = tempfile.mkdtemp(prefix="watchman-runner-drill-")
    jobs = [{"id": "j1", "status": "open", "addressed_to": "hana",
             "title": "Write the brief"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
    _snapshots(tmp, "alpha", jobs, agents)
    _snapshots(tmp, "beta", [], {})

    # Phase 1: the real --once run rings, then dedupes.
    run = runner.make_subprocess_runner(snapshot_dir=tmp)
    ok, stdout = run("alpha")
    if not ok:
        return _fail("phase 1: real --once run failed")
    lines = [json.loads(line) for line in stdout.splitlines()
             if line.strip()]
    if (len(lines) != 1 or lines[0].get("kind") != "wake"
            or lines[0].get("job_id") != "j1"
            or lines[0].get("agent") != "hana"):
        return _fail("phase 1: wake event wrong, got %r" % (lines,))
    ok, stdout = run("alpha")
    if not ok or stdout.strip():
        return _fail("phase 1: second run over same state re-rang")
    print("PASS phase 1: real --once rings once, then dedupes")

    # Phase 2: the full cycle wires through unchanged.
    _snapshots(tmp, "alpha", jobs, agents)
    state = os.path.join(tmp, "watchman-state-alpha.json")
    if os.path.exists(state):
        os.remove(state)
    records, new_journal, diagnostics = \
        runner.run_cycle_with_subprocess(
            ["alpha", "beta"], NOW, priors={}, journal=[],
            snapshot_dir=tmp)
    alpha = records.get("alpha") or {}
    beta = records.get("beta") or {}
    if not alpha.get("watchman_alive") or alpha.get("last_bell") is None:
        return _fail("phase 2: ringing machine has no bell: %r"
                     % (alpha,))
    if beta.get("last_bell") is not None:
        return _fail("phase 2: quiet machine invented a bell: %r"
                     % (beta,))
    if new_journal or diagnostics.get("run_failures"):
        return _fail("phase 2: clean cycle carries journal/failures: "
                     "%r %r" % (new_journal, diagnostics))
    print("PASS phase 2: cycle through real runs, bell only "
          "where the watchman rang")

    # Phase 3: a hanging program is killed at the timeout.
    sleepy = _write_script(tmp, "sleepy.py",
                           "import time\ntime.sleep(30)\n")
    ok, stdout, detail = runner.run_once(
        [sys.executable, sleepy], timeout_seconds=1)
    if (ok, stdout, detail) != (False, "", "timeout"):
        return _fail("phase 3: hanging run not a timeout: %r"
                     % ((ok, stdout, detail),))
    started = time.time()
    pair = runner.make_subprocess_runner(
        command_for=lambda name: [sys.executable, sleepy],
        timeout_seconds=1)("alpha")
    if pair != (False, "") or time.time() - started > 20:
        return _fail("phase 3: runner pair wrong or loop hung: %r"
                     % (pair,))
    print("PASS phase 3: hanging watchman killed at timeout, "
          "failed run, loop unhung")

    # Phase 4: a nonzero exit discards partial stdout.
    partial = _write_script(
        tmp, "partial.py",
        "import sys\nprint('{\"kind\": \"wake\"}')\nsys.exit(3)\n")
    ok, stdout, detail = runner.run_once([sys.executable, partial])
    if (ok, stdout, detail) != (False, "", "exit-3"):
        return _fail("phase 4: nonzero exit kept stdout: %r"
                     % ((ok, stdout, detail),))
    print("PASS phase 4: nonzero exit discards partial stdout")

    # Phase 5: missing program, bad argv, bad machine, raising
    # command_for are all contained, nothing raises.
    ok, stdout, detail = runner.run_once(
        [os.path.join(tmp, "no-such-program")])
    if (ok, detail) != (False, "not-found"):
        return _fail("phase 5: missing program not not-found: %r"
                     % ((ok, stdout, detail),))
    if runner.run_once([]) != (False, "", "bad-argv"):
        return _fail("phase 5: empty argv not bad-argv")
    if runner.run_once([sys.executable, 7]) != (False, "", "bad-argv"):
        return _fail("phase 5: non-string argv part not bad-argv")
    plain = runner.make_subprocess_runner(snapshot_dir=tmp)
    if plain("") != (False, "") or plain(None) != (False, ""):
        return _fail("phase 5: bad machine name raised or succeeded")

    def _raising(name):
        raise RuntimeError("boom")

    if runner.make_subprocess_runner(
            command_for=_raising)("alpha") != (False, ""):
        return _fail("phase 5: raising command_for escaped")
    print("PASS phase 5: missing program, bad argv, bad machine, "
          "raising command_for all contained")

    # Phase 6: a failed run ages honestly; inputs unchanged.
    prior = {"watchman_alive": True, "last_tick": NOW - 1000,
             "last_bell": NOW - 1000, "last_wake": NOW - 1000,
             "restart_ok": True}
    priors = {"alpha": prior}
    journal = [{"kind": "crew-dark", "machine": "beta"}]
    priors_before = copy.deepcopy(priors)
    journal_before = copy.deepcopy(journal)
    records, new_journal, diagnostics = \
        runner.run_cycle_with_subprocess(
            ["alpha"], NOW, priors=priors, journal=journal,
            command_for=_raising)
    carried = records.get("alpha") or {}
    if carried.get("last_bell") != NOW - 1000:
        return _fail("phase 6: carried bell changed: %r" % (carried,))
    if "restart_ok" in carried:
        return _fail("phase 6: old restart success re-spent")
    if priors != priors_before or journal != journal_before:
        return _fail("phase 6: priors or journal mutated")
    if "alpha" not in diagnostics.get("run_failures", []):
        return _fail("phase 6: failed run missing from diagnostics")
    print("PASS phase 6: failed run carries the prior bell, "
          "old restart stripped, inputs unchanged")
    print("ALL PASS (6 phases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
