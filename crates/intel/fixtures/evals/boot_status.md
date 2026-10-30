# OS-041 eval: watchdog status line for the boot screen

## What was built

`intel/store.py` gains the OS-041 record: `build_boot_status()`
renders one frozen line from live inputs — units ({unit,
state}, "active" counts up, anything else counts down and is
named), workers alive (the snapshot presence list the stall
detectors already use), and the latest unresolved alert —
stored under `muse-bus:intel:wd:bootstatus:<room>:<ts>` via
`put_boot_status` / `get_boot_status`. Freshness is a
separate rule, `boot_status_is_stale()`: a record is fresh
at exactly 30s old and stale at 31s, so a killed unit can
hide behind an old green line for at most 30 seconds.
"Last alert" means latest created, not highest severity —
that distinction from WDG-028's top alert is deliberate and
documented on the function, so the checklist line and the
brief line never silently disagree about what they headline.

## Drill result

`intel/drills/boot_status.py`: 8 PASS. Green fixture renders
"Boot: 3/3 units up, 2 workers alive — no open alerts";
killing relay-jobs re-renders "Boot: 2/3 units up, 2 workers
alive — down: relay-jobs — no open alerts"; the latest open
alert is named with severity while a resolved alert is
ignored; the pre-kill record is fresh at +30s and stale at
+31s; the post-kill record is fresh. Suite pins: 5 new tests
in `tests/test_os_boot_status.py` (drill, down naming,
latest-open rule, non-dict tolerance, 30/31 staleness
boundary, key shape + fake-Redis round-trip).

## NOT proven here

- The line rendering from live data on a booted test image
  (no test image in repo): unit states here are fixture
  {unit, state} dicts, not systemctl output, and worker
  presence is a fixture list, not a live snapshot.
- Rowan's boot checklist render (OS-043, not landed): the
  record and key exist for it to read; no checklist view
  consumes them yet.
- The 30s bound on real hardware: it is a rule on the
  record's timestamp, not a measured render latency — the
  checklist must re-render (or re-check staleness) at least
  every 30s for the bound to hold in practice.
