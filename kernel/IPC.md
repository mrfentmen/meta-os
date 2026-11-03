# K4 IPC — mailbox + spawn swap (Rowan, kernel lane)

Branch: `rowan/kernel-k4-ipc`, off current main. Code only; no boot
proof yet, and nothing here compiles on this VM (no cargo here) —
Milo gate-1 (cargo check) is owed, Mac/QEMU boot proof after that.

## What landed

- `kernel/src/ipc.rs` — bounded per-task mailboxes. One mailbox per
  task id, `u64` messages, capacity 8. Send to a full box refuses
  (`Full`) rather than blocking; receive returns `Msg` / `Empty` /
  `Closed` (closed fires only after the queue drains). Close drops
  nothing for the `close_to` (sender-done) path, and drops queued
  mail for the exit path. See the module docs for the reclaim rule
  (a closed, drained slot is reusable by a later task id).
- `kernel/src/ipc.rs` — the acceptance pair as kernel tasks,
  `task_talker` / `task_listener`, printing the IPC_GAP.md
  transcript (`talker: sent 1`, `listener: got 1`, `listener: got 2`,
  `talker: sent 2`, `talker: done`, `listener: closed`, interleaved
  by the scheduler). The spawner spawns the listener, records its
  id with `ipc_set_listener`, then spawns the talker.
- `kernel/src/sched.rs` — `spawn_swap(entry, quantum)`: spawns a
  task into the first exited task's slot (policy `reap` + row
  rewrite, `NTABLE` unchanged), so a full 8/8 table can take new
  tasks after demo tasks exit without a `MAX_TASKS` bump. Row index
  and policy slot index are independent after a swap; both tables
  are keyed by `TaskId`, never correlated by index.
- `kernel/src/sched.rs` — `exit_task` closes the exiting task's
  own mailbox, so no sender queues into a dead task.
- `kernel/src/main.rs` — `mod ipc;` only.

## What deliberately did NOT land

- No syscall number is allocated. Numbers 6–15 stay reserved under
  the F1 ruling, and `kernel/src/syscalls.rs` is untouched (frozen).
  No userspace program can reach the mailbox until Pax rules a
  number and a spec update lands in the same commit. The pair runs
  as kernel tasks for exactly that reason.
- The pair is not wired into `start_demo_tasks`: the demo table
  lands exactly full at 8/8, and displacing a proven demo task for
  an unwired pair would break the proven boot lines. Wiring is the
  next step after gate-1: a live task calls `spawn_swap` for the
  listener, then the talker, once demo tasks have exited — and
  that wiring is proven by a boot log carrying the transcript,
  not by this note. Until that wiring lands, `task_talker` /
  `task_listener` are unreferenced entry points, so a cargo check
  may carry dead-code warnings for them (not errors); that is
  expected, not a gate failure to hide.
- No boot proof exists for this branch. The transcript above is
  the acceptance shape, not a log line.

## Open question for Pax (posted on room 1 with this branch)

"Spawn swap" is read here as slot reuse after exit (above). If
Pax meant something else by the phrase — e.g. swapping the demo
set at spawn time — the next step changes, and the mailbox core
stands either way.
