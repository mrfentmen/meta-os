# dock — pinned apps, and a launch that has an outcome

Status: **RUNS** — `tests/t88_dock` passes in the native host corpus
(`run_native.sh t88_dock`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 3.

## What it is

An ordered list of pinned applications, each with running state, plus the launch
handshake the desktop needs: the dock records intent (`dk_launch`), the
supervisor spawns, and the dock is told the outcome (`dk_result`).

**The dock does not spawn anything and does not own a pid.** Spawning is the
supervisor's job (B-L1-21). A dock that also spawned would be a second authority
over the same process table, and the two would disagree the first time a process
died on its own.

## The three rules that carry it

1. **A launch is pending until it is resolved.** Two clicks in 200 ms are one
   launch, not two processes: a pending request inside `DK_DEDUPE_MS` is refused
   with `E_BUSY` and is not counted as a second request
   (`dk_launches_of` stays at one).
2. **A launch that never reports is a failure.** `dk_expire(now_ms)` turns a
   pending request older than `DK_LAUNCH_TIMEOUT_MS` into a failure and counts
   it (`dk_expiries_of`). Leaving it pending forever is how the dock shows
   "starting" for an app that will never appear.
3. **A running app cannot be unpinned.** Unpinning it would leave a window with
   no dock entry, which is how a running app becomes unreachable. `dk_unpin`
   refuses while `dk_running_at` is true; the app comes off the dock after it
   exits.

## Surface

| Function | Answers |
|---|---|
| `dk_pin`, `dk_unpin`, `dk_move` | the ordered list; move is by index |
| `dk_launch`, `dk_result`, `dk_expire` | the handshake, including the timeout |
| `dk_running_off` | the supervisor reporting an app exited |
| `dk_count`, `dk_id_at`, `dk_name_at` | the list, in dock order |
| `dk_running_at`, `dk_pending_at`, `dk_running_count`, `dk_pending_count` | state |
| `dk_launches_of`, `dk_failures_of`, `dk_expiries_of` | per-app outcomes |

## Where the proof is

`services/tests/t88_dock.goose` — including the double-click dedupe and the
expiry path.
