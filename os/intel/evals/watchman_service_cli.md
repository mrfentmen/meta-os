# Eval: watchman service CLI (Milo, OS-122 follow-up)

## What was wrong

The service loop was proven in-process and the unit file was
proven as a shape, but the command the unit execs had never
run as a process. Running it from the repo root failed at
import time:

```
$ python3 intel/watchman_service.py --machines alpha --cycles 2 \
    --interval 0 --snapshot-dir /tmp/wwcli
ModuleNotFoundError: No module named 'intel'
```

Python puts the script's own directory (intel/) first on
sys.path, not the repo root, so `from intel import
watchman_runner` raised no matter what WorkingDirectory the
unit carried. The sibling watchdog unit does not hit this
because intel/watchdog.py imports no intel modules; the
watchman loop imports a six-module intel chain. As written,
relay-watchman-watch.service would have died at startup.

## Fix

`intel/watchman_service.py` inserts the repo root (parent of
its own directory, /opt/relay on the image) into sys.path
before the intel import, the same bootstrap the intel/*
script entry points already use. No PYTHONPATH, no unit
change, no change to any judgment code.

## Drill

`intel/drills/watchman_service_cli.py`, 4/4 phases PASS,
every subprocess run with PYTHONPATH removed from the
environment:

1. Plain command, 2 cycles against temp snapshots: exit 0,
   2 cycle lines, "service loop stopped after 2 cycles".
2. Empty machine list: exit 0, "cycle 0: 0 machines",
   judging nothing, no invented machine.
3. The unit's own ExecStart line, read out of the unit file
   with /opt/relay swapped for the repo root, the machines
   variable replaced with alpha, and /run/metaos replaced
   with the temp snapshot directory: exit 0, 1-machine cycle.
4. Bad flag: argparse exit 2, no traceback.

## Tests

`tests/test_intel_watchman_service_cli.py`: 5 tests
(plain command, empty machines, unit ExecStart, drill
passes, no em dash in new files). New tests 5/5; full
suite result recorded in the commit message.

## Follow-up: the no-env-file unit shape

Phase 3 of the drill substitutes alpha for
${WATCHMAN_WATCH_MACHINES}, so it never exercised the
shape the unit actually produces with no env file: systemd
expands an unset variable to nothing, leaving a bare
--machines directly before --snapshot-dir, and argparse
with a plain required-value --machines fails that shape
with exit 2 ("expected one argument", reproduced before
the fix). Under Restart=on-failure that is a restart
loop, not the configuration gap the unit header claims:
the header said "with no file the loop cycles with zero
machines", but the command as written would never get
to cycle at all. The other two units do not carry this
hazard: relay-watchdog.service and relay-watchman.service
use fixed ExecStart arguments, no ${VAR} expansion.

Fix: --machines takes nargs="?" with const="", so a bare
--machines reads as an empty list under either systemd
expansion behavior (empty word kept: the phase 2
--machines "" case; empty word dropped: the new phase 5
bare-flag case). No judgment code changed, no unit change:
the ExecStart line is untouched, and the header now states
the mechanism instead of just the claim. Drill now 5/5
phases PASS; CLI tests gain the bare-flag case (6 tests).
Still not proven: a booted service, a systemd restart,
or the live queue reader; the relay.target / image wiring
remains Pax OS-101 work, deliberately untouched.

## Not proven here

A booted service, a systemd restart of the unit, a live
watchman on a booted test image, or the live queue reader
OS-118 still owes. The unit is still not wired into
relay.target wants or any image enablement list; that
wiring is Pax's OS-101 integration and is deliberately
untouched here. The command the unit execs is proven; the
service itself is not.
