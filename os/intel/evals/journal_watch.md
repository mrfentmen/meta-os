# OS-037: journal watch — drill result

Status: DRILL PASS on fixtures (see `journal_watch.log`).

The watch (META_OS.md, crew activity journaling): journald is
the machine's own account of itself, and a relay unit's failure
there becomes a SYSTEM alert record in the same alert store
the dashboard reads. The watch is the watchdog's second loop
input, beside snapshots — it is deliberately NOT a snapshot
detector, so a snapshot tick never waits on journalctl.

## The failure rule

A journal entry fires only when BOTH hold:

1. The unit is a relay unit (name starts with `relay-`). A
   failing sshd or cron unit is the host's business, not the
   crew's, and never becomes a crew alert.
2. The entry is a failure: a systemd failure message
   ("Failed with result", "Main process exited", "Failed to
   start", "entered failed state") OR an err-or-worse journal
   priority (3 or lower). A relay unit logging at err is the
   machine reporting its own failure, and the alert quotes the
   message verbatim so a human can judge transience.

Healthy relay lines (Started, priority 6) stay silent, as do
non-relay failures, unparseable lines, and entries with no
unit (no invented attribution).

## What the watchdog gained

`intel/watchdog.py::detect_journal_failures()` reads
journalctl -o json lines (or parsed entry dicts, either key
shape) and yields one alert per failed unit: kind
`system-failure`, severity `critical`, subjects `[unit]`,
`system_alert` True, and no nick or job field — so no reader
(brief, dashboard, human) can mistake a unit failure for a
worker stall. Failures group by unit (`failure_count` counts
the lines), so a unit failing, restarting, and failing again
in one window is one incident, not a storm; re-reports inside
the WDG-013 cooldown advance `last_seen` only. The suggested
fix names `journalctl -u <unit>` and an operator restart —
the watchdog never restarts a unit itself, per the OS-034
contract (systemd owns process death). The CLI gained
`--journal <file>` for one journal-watch iteration alongside
the snapshot tick (stdout only, never a bus post).

Drill: `intel/drills/journal_watch.py` (10 PASS lines).
Tests: `tests/test_os_journal_watch.py` (15 tests, including
the fake-store round-trip: one `journal_watch_tick` with
`write_alert` as emit writes a record that `query_alerts`
returns, and a re-tick inside the cooldown advances only
`last_seen`). Severity is critical in the alert itself, locked
by these tests and by the `intel/README.md` mapping-table row
— deliberately NOT in `SEVERITY_BY_KIND`, whose lock in
`test_intel_watchdog.py` covers exactly the snapshot
detectors' kinds, and journal watch is not one.

## NOT proven here (honest gaps)

- No real unit was force-failed: there is no test image in
  this repo, so the live half — `systemctl kill` / fail a
  relay unit on the image and watch the alert land in the
  dashboard feed within one service loop — is still owed on
  the test image, as is wiring the journal watch into the
  relay-watchdog.service loop itself (the loop currently
  ticks snapshots only; the journal iteration is a callable
  the service loop can add, not yet a unit flag).
- The dashboard rendering of a SYSTEM record (distinct
  styling vs job alerts) is Rowan's consumption side; the
  record shape it reads is what this task pins.
