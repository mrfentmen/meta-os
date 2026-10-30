# OS-034: restart-ownership contract — drill result

Status: DRILL PASS on fixtures (see `restart_contract.log`).
The contract, from META_OS.md's supervision contract: systemd's
`Restart=` owns process death; the watchdog owns silent-but-alive
stalls; neither double-acts on the other's case.

## The two cases (worker pax, job 7, T0 = 100000)

| Case | Timeline | Watchdog output | systemd side |
|---|---|---|---|
| A: kill -9 + restart | Killed T0+300 (presence + heartbeats stop); back T0+310 (modeled RestartSec 10s, presence restored, heartbeat fresh) | Mid-gap tick: 0 alerts. Post-restart tick: 0 alerts. One `worker-restart` INFO record (id `worker-restart:pax:7`), validated through the store writer, never announced | Restarted the worker; the watchdog did not second-guess it |
| A-control: kill -9, no restart | Same death, ticked past the 10-min stall threshold with presence still gone | Exactly 1 presence-stall alert | Nothing to restart — proves case A's zero comes from the restart, not a blind detector |
| B: SIGSTOP (wedged) | Worker stays in presence (process alive), last activity frozen at T0; ticked past the 10-min progress threshold | Exactly 1 progress-stall alert naming pax, job 7, and the age; 0 presence-stall alerts; no restart note | Nothing: a live process is not restarted, so there is no restart fight |

## What the watchdog gained

`intel/watchdog.py::restart_event_note()` builds the case-A note:
kind `worker-restart`, severity `info`, dedupe key
`worker-restart:<nick>:<job>`, explanation naming the systemd
restart and the absence of a stall alert, fix "no action unless
restarts repeat". Info severity keeps it out of the announcement
path by construction (`format_announcement` yields nothing for
non-critical records), so a handled restart shows in the brief
and dashboard without ever becoming a bus announcement. The
note carries `downtime_seconds` only when the caller observed
it; otherwise the explanation says "brief absence" rather than
inventing a gap length.

Drill: `intel/drills/restart_contract.py` (9 PASS lines).
Tests: `tests/test_intel_restart_contract.py` (7 tests).

## NOT proven here (honest gaps)

- No real systemd restart was observed: there is no test image
  in this repo, and the `relay-worker@<nick>.service` template
  unit exists only as a row in META_OS.md's service table, not
  as a unit file — so its real `RestartSec` value is unpinned
  (the drill models 10s, the watchdog unit's value). The live
  kill -9 / SIGSTOP run on the test image is still owed.
- The stop-the-unit dashboard render for the watchdog itself
  is still owed on the test image (same gap as OS-033).
- Side note for a later cleanup (not changed here, to keep
  this commit to one task): OS-033's unit header still says
  the relay-jobs unit "is not landed yet" — Pax's 2026-10-27
  pull landed `os/services/relay-jobs.service`, so that
  sentence is now stale.
