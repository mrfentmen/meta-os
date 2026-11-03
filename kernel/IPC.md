# K4 IPC — build step (corrected design)

**Design:** `os-build/K4_IPC_DESIGN.md` on `rowan/kernel-k4-design`
(corrections applied there per Pax review: numbers 6/7, Q-I1 swap,
exit-path funnel, pinned gate lines). This branch is the build step
for that design, and it **replaces** the earlier draft on
`rowan/kernel-k4-ipc`, which diverged from it: an 8-message ring of
`u64` values with kernel-task talker/listener pair, no userspace
syscall numbers, and a close/drain channel semantic. Nothing from
that draft's semantics survives here except the exit-path clearing
idea, re-implemented below in the design's terms.

**Status: UNCOMPILED / UNVERIFIED on this VM.** Written against the
kernel tree on current main; no build or boot is claimed. Proof is
the Mac gate (cargo check/build + QEMU boot log through OpenCode 1,
read by Pax) — the same standard as every kernel step before it.
Do not present this branch as compiled or booted.

## What landed (3 files)

- `kernel/src/sched.rs` — mailbox state, in the design's Q-I2 home:
  one box per scheduler row, parallel to `SLEEPS`, kernel-owned
  static storage, no heap, no page sharing. A box holds exactly one
  message: kernel-filled sender id, length, up to 64 payload bytes.
  Helpers: `task_is_live` (row exists and policy task is not
  `Exited`), `ipc_try_send` (false on a full box, no state change),
  `ipc_try_recv` (copies sender header + payload into the caller's
  buffer, empties the box; `None` on empty), `ipc_clear` (discard
  one row's box). `exit_task` calls `ipc_clear(current_id())`
  before `exit_current` — the single funnel for every removal
  path: voluntary exit (syscall 0), entry return (trampoline),
  loader refusal (`run_elf` error arms), ring-3 fault kill
  (page-fault handler). Double fault halts the machine and needs
  no clearing rule. Mail already delivered to another task's box
  survives the sender's exit; only the exiting task's own row is
  cleared here.
- `kernel/src/user.rs` — dispatch only. Syscalls **6 = ipc_send,
  7 = ipc_recv**, added to the inline `match` in `syscall_handler`
  exactly where 0–5 live. `syscalls.rs` is **untouched** (F1
  FROZEN). `ipc_send`: rdi = destination id, rsi = buffer,
  rdx = length 1..=64; returns 0 on success, `u64::MAX` on any
  refusal. `ipc_recv`: rdi = buffer, rsi = capacity >= 72;
  returns total bytes copied (8-byte little-endian sender header
  + payload, 9..=72) on success, `u64::MAX` when empty or
  refused. Validation order is the design's §3 order, all before
  any copy: live destination, mapped buffer, length/capacity in
  range, then box empty (send) / non-empty (receive). Both
  operations are non-blocking: a full box refuses, an empty box
  returns `u64::MAX`; the caller polls, sleeping or yielding
  between polls (the read_key idiom). No blocking receive, no
  wait queue, no wake-on-death path in this step.
- This file — the build note. No `kernel/src/ipc.rs` module, no
  kernel-task talker/listener pair, no `spawn_swap`: those were
  draft mechanisms, not the design. The gate pair are Buffy's
  userspace programs, written against the design's §6 convention
  (fixed spawn-order peer ids from the gate build's loader table;
  `getpid` returns only the caller's own id).

## Literal gate lines (design §7, all present verbatim)

- `user ipc send <sender> -> <dest> len <n>`
- `user ipc recv <receiver> len <n> from <sender>` (total, header included)
- `user ipc send <sender> -> <dest> refused full`
- `user ipc send <sender> -> <dest> refused dead`
- `user ipc send <sender> refused unmapped`
- `user ipc recv <receiver> refused small buffer`
- `user ipc recv <receiver> empty`

Two refusal lines are this build's analogues, not pinned by the
design: `user ipc send <sender> refused bad length` and
`user ipc recv <receiver> refused unmapped`. They change no gate
leg; the pinned legs above are exact.

## Deliberately not in this step

- **Slot budget (Q-I1):** `MAX_TASKS` stays 8. The gate build swaps
  demo programs out of `start_demo_tasks` to make room for the
  talker/listener pair; no table growth, no `spawn_swap` API here.
- **Blocking receive:** a later designed step. It needs
  `block_current`/`unblock` wiring plus the death cases re-proved.
- **Sender filtering / squatting fix:** the design's stated step-1
  limitation stands — any live task can occupy any live task's
  only slot until it receives or exits. Named, not hidden.
- **Slot reuse proof for reap:** `tasks.rs::reap` is unused by this
  kernel. If reap ever lands, its build step must re-prove that
  exit-clearing still holds on the reap path (design Q-I3); this
  step does not assume it.
- **Shared memory / copy-on-write / K3 demand paging:** out of
  scope. A send buffer is validated as mapped at call time and
  refused when unmapped (the `user_write` rule); if K3 lands
  first, its build must say whether a faulting send buffer
  becomes a demand fault or stays a refusal.

## Gate pack mapping (design §7, for the Mac boot log)

Exchange, full-box refusal, empty-receive polling, dead-peer
refusal, sender-survives-exit, negative legs (unmapped send,
undersized receive buffer), third task unaffected, console alive,
no panic — all five legs are expressible through syscalls 6/7
plus the pinned lines above, once Buffy's pair exists. A log
showing only successful exits, without the send/receive lines,
proves nothing.
