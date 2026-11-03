# Contract — `dock`

Status: **RUNS** — `services/tests/t88_dock.goose`, on the host shim. Not started by a
supervisor; nothing starts a service yet.

## What it is

The pinned-application list, its order, and the launch handshake. The dock records
*intent* and *outcome*; it never spawns. Spawning is the supervisor's (see
`services/supervisor`), and a dock that also spawned would be a second authority over the
same process table.

## The three rules

1. **A launch is pending until it is resolved.** Two clicks inside `DK_DEDUPE_MS` (1500 ms)
   are one launch: the second is `E_BUSY` and does not increment the launch counter.
2. **A launch that never reports is a failure.** `dk_expire` turns a pending request older
   than `DK_LAUNCH_TIMEOUT_MS` (5000 ms) into a failure and clears pending, so the dock
   cannot show "starting" for an app that will never appear.
3. **A running app cannot be unpinned.** `E_BUSY`. Unpinning it would leave the window with
   no dock entry, which is how a running app becomes unreachable.

## API

| function | returns | notes |
|---|---|---|
| `dk_init()` | — | empty dock, ids from 1 |
| `dk_pin(name)` | `(id, code)` | duplicate name → `E_STATE`, 13th pin → `E_NO_SPACE` |
| `dk_unpin(id)` | code | refuses while running, and while a launch is pending |
| `dk_move(id, index)` | code | shifts the array; index is the destination slot |
| `dk_launch(id, now_ms)` | code | sets pending; dedupe window applies |
| `dk_result(id, ok)` | code | supervisor's answer: clears pending, sets running / failure |
| `dk_expire(now_ms)` | count expired | call on every dock tick |
| `dk_id_at(i)` / `dk_name_at(i)` / `dk_running_at(i)` / `dk_pending_at(i)` | entry | array order **is** dock order |
| `dk_launches_of` / `dk_failures_of` / `dk_expiries_of` | counters | per item, for the dashboard |

`dk_move` shifts entries rather than storing a sort key: reading the dock top to bottom
needs no sort and no second index, which is the whole reason the order cannot drift from
what is on screen.

## Failure modes, all driven by the test

- **Double click** — second `dk_launch` inside the window is `E_BUSY`, `launches` still 1.
- **Silent spawn** — pending past the timeout is expired, counted as a failure, and the app
  is not marked running.
- **Unpin while running / pending** — `E_BUSY` both ways.
- **Move out of range** — `E_INVAL`, order unchanged.
- **Duplicate pin** — `E_STATE`. Case-sensitive, deliberately: two entries that differ only
  by case are two entries a user cannot tell apart.
- **Full dock** — 12 pins, the 13th is `E_NO_SPACE`.

## Restart semantics

All memory, including counters. `dk_init` empties the dock: **pins do not survive a
restart**, and this build has no persistence hook for them. The counter reset is worse than
the pin loss — a running app that is no longer in the dock after a supervisor restart is
exactly rule 3's failure, so the restart path must re-pin from config *before* the session
is told anything is running.

## Limits

`DK_MAX` 12, `DK_NAME_MAX` 16 (15 usable), `DK_DEDUPE_MS` 1500, `DK_LAUNCH_TIMEOUT_MS`
5000. Storage is 12 × ~72 bytes, measured by `size_audit.py`.
