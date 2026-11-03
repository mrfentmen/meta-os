# Record — the task lifecycle, from the code

Scope: `kernel/src/tasks.rs` (policy and state) and `kernel/src/sched.rs` (the wiring that
actually switches). Every claim cites a line range; where the two files disagree, that is
listed at the end.

## States

`TaskState` (`tasks.rs`, lines 142-160): `Ready` (eligible), `Running` (on the CPU), `Blocked`
(not eligible until unblocked), `Exited` (finished, slot held until reaped). A blocked task is
never picked; an exited task is never resumed.

## Identity

`TaskId` wraps a `u64`; ids start at 1 and **0 is never a task** (`tasks.rs`, lines 108-140).
`TaskId::is_valid` is the only validity test, and `sched.rs` uses a separate `TaskId::new(0)`
as its own "scheduler context" sentinel, which is why 0 must stay invalid.

## Context

`Context` (`tasks.rs`, lines 164-205) carries `rsp`, `rbp`, `rbx`, `r12`-`r15`, `rip`,
`rflags` — the callee-saved set plus the resume point and flags any switch must preserve. It is
data; loading it outside the trampoline's register discipline is undefined behaviour, not a
switch.

`Context::initial(stack_top, entry)` (lines 207-232) refuses — returns `None` — when the entry
is 0, the stack top is 0, or the top is not 16-byte aligned. Flags start at `0x202` (IF set).
A first switch is therefore validated at spawn, not at switch time.

## Stack

`Stack::new(bottom, size)` (`tasks.rs`, lines 238-290) refuses a zero size, a size that is not
a page multiple, an overflow, and a misaligned top. The module checks one stack's own shape;
it cannot see other owners' ranges, so overlapping stacks are caller error.

## The wiring that runs

`kernel/src/sched.rs`:

- `spawn_task` (`sched.rs:218-239`) allocates a 16 KiB heap stack, validates it with `Stack::new`,
  asks the scheduler for an id with `Context::initial(top, trampoline)`, and fills the parallel
  tables (`CTXS`, `IDS`, `KSTACK_TOPS`, `ENTRIES`, `SLEEPS`). Spawn refuses past `MAX_TASKS`
  (8) or on any validation `None`.
- `task_trampoline` (lines 203-215) is what a task actually starts at: it looks up its own
  entry by id, runs it, and calls `exit_task()` when the entry returns. A returned task and an
  exited task take the same path, which is why `hello` needs no explicit exit to be reaped.
- `yield_task` (`sched.rs:141-152`): wake expired sleepers, then switch to the next ready task, or stay.
- `sleep_task` (`sched.rs:154-172`): writes the wake tick into `SLEEPS`, blocks the current task, switches.
- `exit_task` (`sched.rs:174-189`): wakes expired, asks the scheduler to exit, switches to the next ready
  task or back to the scheduler context; the slot stays `Exited`.
- `wake_expired` (`sched.rs:191-201`) runs in scheduler context only — the timer IRQ just increments
  `TICKS`, it never unblocks a task inside interrupt context.

## What the boot log proves

`K5-boot.txt` / `K1-boot.txt`: `A`/`B` alternate (round robin), `C sleeping 200 ticks` then
`C awake` (sleep/wake), and `ps` in `K7-boot.txt` shows six `Exited` rows and one `Running` —
states reflect reality rather than a status word invented for the display.

## Disagreements and gaps

1. `tasks.rs`'s module header still says **UNWIRED, NOT A BOOT VERDICT** (lines 1-30). It is
   wired in `main.rs` and its scheduler runs in the boot logs. The header is stale; the file is
   Rowan's to correct.
2. `MAX_TASKS` is 8 and there is **no reap/respawn**: a task slot that exits keeps its index
   forever, so a long-running system with repeated spawns exhausts the table. This is stated in
   `sched.rs`'s header as a K5 property, not a bug, but it is the first thing that breaks on a
   real workload.
3. `tasks.rs` implements a `reap`/respawn policy that `sched.rs` does not call — the policy
   exists and the wiring ignores it, so `ps` shows ever-growing `Exited` rows.
