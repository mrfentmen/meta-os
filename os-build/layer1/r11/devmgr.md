# devmgr — Round 11 record

Source: `services/devmgr/README.md` only (no `.goose` file) · Test: none · Status: NOT A SERVICE

**Finding, first line:** `services/devmgr/` contains a README and nothing else. It is the old
name for the device table, which lives in `services/devices/devices.goose`. Nothing imports
`devmgr`, the supervisor does not start it, and there is no module for a test to import. The
six-task pass cannot be performed on a directory with no code; what it can do is stop the
README from claiming otherwise.

## 1. Limits — NOT APPLICABLE

`os-build/layer1/LIMITS.md` lists no `devmgr` constant, because there is no source file to
declare one. The device table's limit is `DEV_MAX = 16` in `services/devices/devices.goose`,
recorded against `devices` and driven by `tests/t77_gaps` — not a fact about this directory.

## 2. Refusals — NOT APPLICABLE

No code, so no refusal path exists here. The device table's refusals are `devices`'.

## 3. Restart — NOT APPLICABLE

Nothing starts, so nothing restarts. The supervisor's table has no `devmgr` entry.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| — | — | none | **FINDING: `devmgr` is not a service id in `services/callmatrix/callmatrix.goose`** |

`SVC_DEVICES = 8` is the id for the real device table. `devmgr` appears nowhere in the matrix,
which is correct for a retired name and wrong for anything that still imports it. A search of
`import devmgr.` across `services/` returns nothing.

## 5. Load — NOT APPLICABLE

There is no test and nothing to run, so there is no load line. A marker here would be a number
the coordinator could not fill.

## 6. README truth pass — PROVEN

The README said **“Status: WRITTEN (not COMPILED). Source exists”** — both halves false: there
is no source here, and the real implementation has been RUNS under `devices` since `t77_gaps`.
It also carried the generic template sections (“Verified via goose-mcp”, “Not verified:
Compilation”) that describe a unit that does not exist.

It now says, in its first paragraph, that this is not a separate service, names
`services/devices/devices.goose` as the implementation, and points at that service's record
instead of repeating a contract it does not own.
