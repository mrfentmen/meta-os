# dock — Round 11 record

Source: `services/dock/dock.goose` · Test: `services/tests/t117_dock_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `DK_MAX` | 12 | `dock.goose` | driven: twelve pins fit, the thirteenth is `E_NO_SPACE` and the count does not move | `t88_dock`, `t117_dock_r11` |
| `DK_NAME_MAX` | 16 | `dock.goose` | driven: 15 bytes accepted, 16 refused with `E_NOROOM` (the last byte is the terminator) | `t88_dock`, `t117_dock_r11` |

Two timing constants are not in LIMITS.md because they are not capacities, and they are the two
edges this round adds: `DK_DEDUPE_MS` (a second click one millisecond inside the window is
`E_BUSY`; exactly at the window it is a new launch) and `DK_LAUNCH_TIMEOUT_MS` (one millisecond
early expires nothing; exactly at the timeout the launch becomes a failure). Both are driven by
`t117_dock_r11`. `t88` covers them with round numbers only.

Run note: `t117_dock_r11` was written in this pass and has not been executed by this worker. The
boundary rows become evidence only when the coordinator's run appears in section 5; the `t88`
rows are already measured.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| empty name | `E_INVAL` | `t88`, `t117`: "an empty name is E_INVAL" |
| name with a control byte | `E_INVAL` | `t117`: "a control byte is E_INVAL" |
| duplicate name | `E_STATE` | `t88`, `t117`: "a duplicate name is E_STATE" |
| name of 16 bytes | `E_NOROOM` | `t88`, `t117`: "a name of DK_NAME_MAX bytes is E_NOROOM" |
| thirteenth pin | `E_NO_SPACE` | `t88`, `t117`: "the next pin is E_NO_SPACE" |
| move to a negative index or past the end | `E_INVAL` | `t88`, `t117`: both indices |
| unknown id on move, launch, result, unpin, running-off | `E_NOTFOUND` | `t88`, `t117` |
| launch while running, or inside the dedupe window | `E_BUSY` | `t88`, `t117`: both sides of the window |
| unpin while running or pending | `E_BUSY` | `t88`, `t117` |
| result with no pending request | `E_STATE` | `t88`, `t117`: "a result with no request is E_STATE" |
| run-off of an app that is not running | `E_STATE` | `t88`, `t117` |

## 3. Restart — NAMED GAP

The dock's table is in memory and owned by the dock process; a supervisor restart rebuilds it
from whatever pins the shell or the desktop last wrote, and the launch counters (`launches`,
`failures`, `expiries`) are lost. The loss is bounded and visible: a restart cannot double-launch
anything, because a pending request does not survive, but it also cannot report why the previous
run's launches failed. No restart was run for this record, so continuity is not claimed. If pins
are to survive a restart they need a settings key, which does not exist yet; that is the gap.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | none | dock imports `common.err` only; it calls no service | — |
| in | supervisor | the supervisor reports a launch outcome through `dk_result` | no edge: the matrix carries dock's own row (`SVC_DOCK`), not a caller row for the supervisor |
| in | session/desktop | a click calls `dk_launch` | no edge: the desktop is a program, not a matrix service |
| declared but dormant | storage, log, settings, session | the matrix allows all four | yes: `cm_set(SVC_DOCK, STORAGE | LOG | SETTINGS | SESSION)` |

**FINDING: the supervisor calls `dk_result` and has no matrix edge to do so.** The matrix's
`SVC_SUPERVISOR` row allows log, watchdog, session, audit, time and agenthost; dock is absent.
The dock is passive today (the host driver calls it), but a supervisor that reports launch
outcomes is a real caller and the table does not say so. This is for room 1 / the matrix owner;
nothing here depends on it yet.

The dock spawns nothing and owns no pid, by design; the launch handshake is a report, not an
authority.

## 5. Load — NAMED GAP

The test runs one hundred launch handshakes (launch → success → running-off) with the clock
advanced two seconds per cycle, ten times a normal batch for this service. It approaches
`DK_DEDUPE_MS`/`DK_LAUNCH_TIMEOUT_MS` on every iteration and the launch counter must reach one
hundred; no table capacity is approached because one app is reused.

RUNS pass=67 fail=0 · `LOAD dock ops=100 ok=100 refused=0`

## 6. README truth pass — PROVEN

- The README was already true: RUNS, `t88_dock`, the three rules, the no-pid boundary. No stale
  sentence was found.
- One addition: "Where the proof is" now names `t117_dock_r11` alongside `t88_dock`, because the
  boundary cases are the new evidence and a reader should find them from the service page.
