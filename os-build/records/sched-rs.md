# `kernel/src/sched.rs` — wiring record (B243)

Scope: `kernel/src/sched.rs` only. The policy (states, pick order, spawn
validation) lives in `kernel/src/tasks.rs` and is recorded separately; this
file is the half that actually switches the CPU. Every claim cites a line
range from the file on `main`, 2026-11-02. Kernel source is Rowan's pen;
nothing here edits it.

## What sched.rs owns

| Thing | Where | What it is |
|---|---|---|
| `MAX_TASKS = 8` | `sched.rs:21` | hard slot limit; no reap, so a used slot is never freed in K5 |
| `CTXS`, `IDS`, `ENTRIES`, `SLEEPS`, `KSTACK_TOPS` | `sched.rs:28-40` | parallel arrays in spawn order; slot index is spawn order |
| `CUR` | `sched.rs:42` | the task on the CPU; `TaskId::new(0)` means the scheduler context |
| `SCHED_CTX` | `sched.rs:45` | `kernel_main`'s own context, the first switch source |
| `SCHED`, `SLOTS` | `sched.rs:46-47` | the `tasks::Scheduler` and its caller-owned slot table |

The module header states the division of labour and the cooperative rule
(`sched.rs:1-12`).

## The context switch

`switch_to(old, new)` (`sched.rs:75-107`) is the only code that moves
execution:

- saves `rflags` (pushfq/pop rax), `rsp`, `rbp`, `rbx`, `r12`-`r15`, and the
  resume `rip` (a local label) into `*old` at fixed byte offsets;
- loads the same set from `*new`, pushes/pops the saved flags, then
  `jmp qword ptr [rsi + 56]` to the new `rip`;
- clobbers only `rax`, which is caller-saved, so no caller register leaks
  across.

The surrounding helpers are the bookkeeping that makes that safe:
`goto` keeps `CUR` correct across a task-to-task switch, `enter` performs
the first switch from `SCHED_CTX`, and `back_to_sched` returns when no task
is ready (`sched.rs:75-140`).

## Spawn

`spawn_task(entry, quantum)` (`sched.rs:218-239`):

1. refuses at `NTABLE >= MAX_TASKS` (returns `None`);
2. allocates a 16 KiB stack from the kernel heap with `Box::new` and leaks it
   deliberately (the task owns it for the machine's life);
3. validates it with `tasks::Stack::new`, asks `tasks::Scheduler::spawn` for
   an id, and builds a first context with `Context::initial(top, trampoline)`;
4. fills `CTXS`, `IDS`, `KSTACK_TOPS`, `ENTRIES`, `SLEEPS` in spawn order and
   increments `NTABLE`.

Every refusal returns `None`; no task is invented and no slot is overwritten.

## Sleep, yield, exit, wake

- `yield_task` (`sched.rs:141-152`): wake expired sleepers, ask
  `Scheduler::yield_now` for the next task, switch if one exists.
- `sleep_task(ticks)` (`sched.rs:154-172`): store `now.saturating_add(ticks)`
  in this task's `SLEEPS` row, block it, switch or go back to the scheduler.
- `exit_task` (`sched.rs:174-189`): wake expired, mark the current task
  exited through `Scheduler::exit_current`, switch to the next ready task or
  `back_to_sched`, then `unreachable_unchecked`. The slot stays `Exited`.
- `wake_expired` (`sched.rs:191-201`): runs in the scheduler context only;
  it scans `SLEEPS`, clears expired deadlines, and unblocks those ids. The
  timer IRQ never calls it.
- `task_trampoline` (`sched.rs:203-215`): entry every task starts at; it
  looks up its own entry by id, runs it, and calls `exit_task` when the entry
  returns. A returned task and an explicit exit take the same path.

## The run loop

`sched_init` builds the scheduler over `SLOTS` (`sched.rs:251-256`).
`run()` (`sched.rs:262-281`) loops: wake expired, `schedule()`, switch to the
picked task, or `hlt` when nothing is ready. The timer IRQ wakes the CPU for
the next decision.

## Task set and the running policy

`start_demo_tasks` (`sched.rs:650-661`) registers vector 128 and spawns
exactly seven tasks at priority 0 with `quantum = u32::MAX`: A, B, C, hello,
sleeper, crasher, console. That is the `STATUS tasks=7` in the logs and one
spare slot.

Because every task is priority 0 and the quantum is `u32::MAX`, the policy
that actually runs is pure round-robin. `tasks.rs` implements priority
selection and quantum expiry (`tasks.rs:466-490`, `:542-590`, `:678-710`),
but nothing in `sched.rs` calls `on_timer_tick`; `timer_handler`
(`interrupts.rs:502-512`) only increments `TICKS` and sends EOI. **No
preemption runs today.** Switches happen only at `yield`, `sleep`, `exit`,
and the run loop.

## Refusals

| Request | Result | Where |
|---|---|---|
| spawn past 8 rows | `None` | `sched.rs:218-220` |
| bad stack / entry / context | `None` (propagated) | `sched.rs:224-235`; `tasks.rs:318-350` |
| yield with nothing else ready | no switch | `sched.rs:141-152` |
| sleep with no ready task | `back_to_sched` | `sched.rs:171-176` |
| exit with no ready task | `back_to_sched` | `sched.rs:185-189` |

## Findings

1. `tasks.rs`'s header still describes the scheduler as unwired and
   `Cargo.lock` as absent (`tasks.rs:1-30`). This file wires it and
   `main.rs:178-179` starts it; the header is stale (Rowan's file).
2. `tasks.rs` implements `reap` (`tasks.rs:658-676`) but `sched.rs` never
   calls it, so exited slots are never reused. This is the first limit a
   real workload hits.
3. The module comment says "no reap in K5" (`sched.rs:21`) and that matches
   the wiring, not a defect by itself — recorded so nobody assumes respawn
   exists.
