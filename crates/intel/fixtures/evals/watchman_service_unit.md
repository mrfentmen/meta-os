# OS-122 eval: the watchman watcher as a systemd unit (Milo follow-up)

This closes the gap the service-loop eval named: the `__main__` entry point
was "the command a unit would exec, not a unit file". It is now the command
a unit file execs.

## What was built

- `os/services/relay-watchman-watch.service`: runs
  `python3 /opt/relay/intel/watchman_service.py --machines
  ${WATCHMAN_WATCH_MACHINES} --snapshot-dir /run/metaos` as the relay user,
  ordered after relay-watchman.service, Restart=on-failure with RestartSec=5,
  PartOf relay.target, WantedBy relay.target.
- The OS-034 split is preserved for the watcher itself: systemd owns the
  watcher process dying (a loud crash, restarted), while a watchman going
  silent stays a crew-dark judgment the loop makes, never a restart fight.
- Machine list: WATCHMAN_WATCH_MACHINES from the optional
  /etc/metaos/watchman-watch.env. No machine-naming convention exists in this
  repo yet, so the unit names no machine itself and says so in its header:
  with no list the loop cycles empty and judges nothing, a configuration gap,
  not a passing watch. Naming the machines belongs to the image integration
  (Pax OS-101) that wires the per-machine snapshot files.
- `intel/watchman_service.py` docstrings updated: the module no longer says
  it is not a systemd unit; it points at the unit file.
- Pinning tests: `tests/test_intel_watchman_service_unit.py` (5 tests:
  ExecStart shape, ordering/restart/identity, header gap statements, module
  points at the unit, no em dash in the unit file).
- Docs: `intel/README.md` watchman section and `plan/META_OS.md` section 4
  record the unit and its gaps.

## Verification

- py_compile on the touched Python files plus the new test file: clean.
- New tests: 5/5 PASS.
- systemd-analyze verify: exit 0 against the unit file, with no output line
  naming this unit (the only output was unrelated host warnings about a
  rsyslog dropin and host timers); a syntax check only, as the header
  states.
- Full suite by discover: baseline plus 5 new tests, only the known
  pre-existing environmental failures, verified identical on the clean tree
  via git stash.

## Not proven here

Service active at boot (the unit is not wired into relay.target wants or any
image enablement list yet; that wiring is Pax's OS-101 integration, not
claimed here), a systemd restart of this unit on the test image, a live
watchman on a booted test image, or the live queue reader OS-118 still owes.
No behavior of the loop itself changed: this follow-up adds the unit file,
its tests, and its docs only.
