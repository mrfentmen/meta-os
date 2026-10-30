"""Watchman service CLI drill (Milo lane, OS-122 follow-up).

The service loop was proven in-process (serve_cycles) and the
unit file was proven as a shape (ExecStart text, ordering,
restart, identity), but the command the unit actually execs
had never run as a process: python3 intel/watchman_service.py
failed at import time, because Python puts the script's own
directory (intel/) first on sys.path, not the repo root, so
"from intel import ..." raised ModuleNotFoundError no matter
what WorkingDirectory the unit carried. The unit would have
died at startup. The bootstrap in watchman_service.py fixes
that; this drill proves the fix, with no PYTHONPATH set, so
no environment variable is load-bearing.

Five checks, all as subprocesses from the repo root:

1. The plain command runs: --machines alpha --cycles 2
   --interval 0 against a temp snapshot directory exits 0,
   prints one cycle line per cycle, and prints the stopped
   line naming 2 cycles.
2. The config-gap case runs: --machines "" exits 0 and
   reports 0 machines, judging nothing, instead of crashing
   or inventing a machine.
3. The unit's own ExecStart runs: the ExecStart line is read
   out of os/services/relay-watchman-watch.service, /opt/relay
   is swapped for the repo root, ${WATCHMAN_WATCH_MACHINES}
   is replaced with alpha, /run/metaos is replaced with the
   temp snapshot directory, and --cycles 1 --interval 0 are
   appended. That exact command exits 0 with a cycle line.
   (The unit file itself is not edited here: enablement into
   relay.target and the image remains Pax OS-101 work.)
4. A bad flag is argparse's exit 2, not a traceback crash:
   the CLI contract fails cleanly.
5. The no-env-file unit shape runs: a bare --machines
   directly before --snapshot-dir (what the unit's
   ExecStart becomes when systemd expands an unset
   ${WATCHMAN_WATCH_MACHINES} to nothing) exits 0 and
   cycles empty, instead of argparse's exit 2, which
   under Restart=on-failure would restart-loop the unit
   rather than report the configuration gap. Phase 2
   (--machines "") proves the empty argument; this phase
   proves the missing argument, the shape systemd
   actually produces.

What this drill does NOT claim, stated plainly. It proves
the command the unit execs, not a booted service: no systemd
unit is started here, no restart is observed, no live
watchman runs on a booted test image, and the per-machine
snapshot files are still the interface until Pax OS-118's
live queue reader lands. No bus post, no live Redis, no
network.

Runs unattended: python3 intel/drills/watchman_service_cli.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SERVICE = os.path.join(ROOT, "intel", "watchman_service.py")
UNIT = os.path.join(ROOT, "os", "services",
                    "relay-watchman-watch.service")


def _fail(message):
    print("FAIL: %s" % message)
    return 1


def _clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _write_fixture(tmp):
    jobs = [{"id": "j1", "status": "open", "addressed_to": "hana",
             "title": "Write the brief"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
    for name, value in (("jobs", jobs), ("agents", agents)):
        with open(os.path.join(
                tmp, "watchman-%s-alpha.json" % name),
                "w", encoding="utf-8") as handle:
            json.dump(value, handle)


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=120, cwd=ROOT, env=_clean_env())


def main():
    tmp = tempfile.mkdtemp(prefix="watchman-service-cli-")
    _write_fixture(tmp)

    proc = _run([sys.executable, SERVICE, "--machines", "alpha",
                 "--cycles", "2", "--interval", "0",
                 "--snapshot-dir", tmp])
    if proc.returncode != 0:
        return _fail("phase 1: plain command exited %d: %s%s"
                     % (proc.returncode, proc.stdout, proc.stderr))
    if proc.stdout.count("cycle ") != 2:
        return _fail("phase 1: expected 2 cycle lines: %r"
                     % proc.stdout)
    if "service loop stopped after 2 cycles" not in proc.stdout:
        return _fail("phase 1: stopped line missing: %r" % proc.stdout)
    print("PASS phase 1: plain command runs 2 cycles, exit 0")

    proc = _run([sys.executable, SERVICE, "--machines", "",
                 "--cycles", "1", "--interval", "0",
                 "--snapshot-dir", tmp])
    if proc.returncode != 0:
        return _fail("phase 2: empty machines exited %d: %s%s"
                     % (proc.returncode, proc.stdout, proc.stderr))
    if "cycle 0: 0 machines" not in proc.stdout:
        return _fail("phase 2: expected 0-machine cycle line: %r"
                     % proc.stdout)
    print("PASS phase 2: empty machine list cycles empty, exit 0")

    with open(UNIT, encoding="utf-8") as handle:
        unit_text = handle.read()
    match = re.search(r"^ExecStart=(.+)$", unit_text, re.MULTILINE)
    if not match:
        return _fail("phase 3: no ExecStart line in unit file")
    command = match.group(1).strip()
    command = command.replace("/opt/relay", ROOT)
    command = command.replace("${WATCHMAN_WATCH_MACHINES}", "alpha")
    command = command.replace("/run/metaos", tmp)
    argv = command.split() + ["--cycles", "1", "--interval", "0"]
    proc = _run(argv)
    if proc.returncode != 0:
        return _fail("phase 3: unit ExecStart exited %d: %s%s"
                     % (proc.returncode, proc.stdout, proc.stderr))
    if "cycle 0: 1 machines" not in proc.stdout:
        return _fail("phase 3: expected 1-machine cycle line: %r"
                     % proc.stdout)
    print("PASS phase 3: unit ExecStart command runs, exit 0")

    proc = _run([sys.executable, SERVICE, "--bogus-flag"])
    if proc.returncode != 2:
        return _fail("phase 4: bad flag exited %d, expected 2: %s%s"
                     % (proc.returncode, proc.stdout, proc.stderr))
    if "Traceback" in proc.stderr:
        return _fail("phase 4: bad flag raised a traceback")
    print("PASS phase 4: bad flag exits 2 cleanly")

    proc = _run([sys.executable, SERVICE, "--machines",
                 "--snapshot-dir", tmp,
                 "--cycles", "1", "--interval", "0"])
    if proc.returncode != 0:
        return _fail("phase 5: bare --machines exited %d: %s%s"
                     % (proc.returncode, proc.stdout, proc.stderr))
    if "cycle 0: 0 machines" not in proc.stdout:
        return _fail("phase 5: expected 0-machine cycle line: %r"
                     % proc.stdout)
    print("PASS phase 5: bare --machines cycles empty, exit 0")

    print("ALL PASS: watchman service CLI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
