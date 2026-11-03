# K4 pair+swap — IPC gate pair boot (Rowan, kernel lane)

**Parent:** `rowan/kernel-k4-ipc2 @ f654ed5` (Milo gate-1 GREEN
2026-11-02; Mac boot log still owed for that branch). This branch
stacks on ipc2 — it does not re-implement the mailboxes — so the
merge order is ipc2 first (after its Mac log), then this branch.
Merging this branch alone would carry ipc2's files with it and
bypass that hold; do not do that.

**Status: UNCOMPILED / UNVERIFIED on this VM.** Written against
the ipc2 tree; no build or boot is claimed. Proof is the Mac gate
(cargo check/build + QEMU boot log through OpenCode 1, read by
Pax) — the same standard as every kernel step before it. Do not
present this branch as compiled or booted.

## The swap (Pax assignment, bus 2026-11-02: "K4 pair+swap build")

`MAX_TASKS` stays 8 and no `spawn_swap` API is added: the swap is
the gate build swapping demo programs out of `start_demo_tasks`,
exactly as the corrected design's §8 Q-I1 answer prescribes. Hello
and crasher are swapped out, in their exact slots, so every other
id stays stable. Hello/crasher still build and stage (they are
still in `kernel/build.rs` BINS and `build_userspace.py`
PROGRAMS); they simply do not boot here, and their proofs live
on main.

## Loader table — the pair's contract (design §6)

Spawn order is id order (`Scheduler::new` starts `next_id` at 1,
`spawn_task` fills in spawn order, no reap in K5):

| spawn | task | id | userspace stack |
|---|---|---|---|
| 1 | task_a (kernel demo) | 1 | — |
| 2 | task_b (kernel demo) | 2 | — |
| 3 | task_c (kernel demo) | 3 | — |
| 4 | talker | 4 | slot 1 |
| 5 | sleeper (third task, kept) | 5 | slot 0 |
| 6 | listener | 6 | slot 2 |
| 7 | console | 7 | — |
| 8 | readkey (LAST, unchanged) | 8 | slot 3 |

Talker sends to fixed id 6; listener expects sender id 4. Both
programs check their own id via `getpid` (syscall 3) at start
and exit 1 on mismatch, so a reordered table fails loudly
instead of misrouting. Ustack budget holds at 4 (sleeper,
talker, listener, readkey) — `take_ustack`'s 4-program cap is
unchanged. Link bases (same 0x10_0000_0000 spacing as the
existing programs): talker 0x640000000000, listener
0x650000000000.

## What landed (7 files)

- `os-build/userspace/user/src/bin/talker.rs` — sends one
  message (`IPC-OK`, 6 bytes) to id 6 via syscall 6, retrying
  with `yield` on refusal (bounded 1000 tries), then exits 0.
  Prints `talker: sent` on success.
- `os-build/userspace/user/src/bin/listener.rs` — polls
  syscall 7 with a 72-byte buffer, yielding between polls
  (design §6 polling pattern, never spinning), bounded
  200,000 polls; on success checks the kernel-filled sender
  header == 4, prints `listener: got IPC-OK`, exits 0.
- `os-build/userspace/user/src/lib.rs` — `sys_ipc_send` /
  `sys_ipc_recv` wrappers (syscalls 6/7). No other syscall
  numbers touched; `syscalls.rs` untouched (F1 FROZEN).
- `kernel/build.rs` — BINS gains `talker`, `listener`.
- `os-build/userspace/build_userspace.py` — PROGRAMS gains
  talker / listener at the next two bases.
- `kernel/src/user.rs` — `TALKER_ELF` / `LISTENER_ELF`
  `include_bytes!` + `task_talker` / `task_listener` entries;
  module doc now says six ELFs.
- `kernel/src/sched.rs` — `start_demo_tasks` swap only. No
  mailbox, scheduler, or console change; ipc2's code is
  inherited unchanged from the parent.

## Expected gate-boot lines (once the Mac log exists)

Kernel pinned lines from ipc2 (design §7): `user ipc send 4 ->
6 len 6` and `user ipc recv 6 len 14 from 4`, plus the programs'
own `talker: sent` / `listener: got IPC-OK`. Console alive
throughout, sleeper as the unaffected third task, no panic.

## Deliberately not in this step

- **Other §7 gate legs:** full-box refusal, dead-peer refusal,
  sender-survives-exit, and the negative legs (unmapped send,
  undersized receive buffer) are not exercised by this pair;
  they need further gate programs and are named, not claimed.
- **Blocking receive:** a later designed step (see ipc2 note).
- **The divergent draft:** `rowan/kernel-k4-ipc @ bd4e003`
  (8-message `u64` ring, kernel-task pair, no syscall numbers)
  is superseded by the corrected design + ipc2. Nothing from
  it is used here, and it must not be merged or revived.
- **Slot reuse / reap:** `tasks.rs::reap` is still unused;
  nothing here assumes it.
