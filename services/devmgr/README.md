# `devmgr` — retired name, not a service

**Status: NOT A SERVICE.** There is no `.goose` file in this directory and nothing imports
`devmgr`. The device table was implemented as `services/devices/devices.goose`, which is RUNS
and driven by `tests/t77_gaps`.

## What this directory is

An old name kept so an existing path does not 404. It is not in the supervisor's table, not in
the call matrix (the device table is `SVC_DEVICES = 8`), and not in `LIMITS.md` — the device
table's `DEV_MAX = 16` belongs to `devices`, and is recorded against it.

## Where to look

- Implementation and contract: `services/devices/devices.goose`, `services/devices/README.md`.
- Round 11 evidence for this directory: `os-build/layer1/r11/devmgr.md` (it records that the
  six-task pass is not applicable, with the reason).

## Deviations

- The README previously claimed “Status: WRITTEN (not COMPILED). Source exists.” Neither was
  true. It now says what the directory is.
