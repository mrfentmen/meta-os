# Proposals for the reserved numbers (BF4-08)

Pax's rule: the F1 freeze holds — 0 exit, 1 write, 2 sleep, 3 pid, 4 yield,
5 read_key, 6–15 reserved. **Nothing here is allocated.** These are proposals,
written so the 2026-11-02 ruling is a yes/no on a concrete signature instead of
a design session under deadline. Every number below is a *request* for a
reserved slot, and every one of them is currently blocking something already
written and already tested.

Source for the "who needs it" column: `SERVICES_SYSCALL_MAP.md`, generated from
the corpus by `gen_services.py`. Six proposals, in the order they block work.

---

## P1 — `sys_ticks`: read the monotonic clock

```goose
extern fn sys_ticks() -> i64 = "sys_ticks";
```

**Shape.** `int64_t sys_ticks(void)`. No buffer, no allocation, no failure.

**What it returns.** A tick count that never goes backwards, at a rate the
kernel publishes in `BootInfo`. Services convert to milliseconds with the rate
they were told; nothing in `services/` assumes a frequency, and one that did
would be wrong on the next machine.

**Why it cannot be faked above the ABI.** `sys_yield` (4) gives up the CPU but
says nothing about time. Every wait loop in this corpus is
`let t0 = sys_ticks(); while sys_ticks() - t0 < ms { sys_yield(); }`. Without
ticks, `sys_yield` is the only clock and a wait either spins forever or sleeps
forever.

**Blocked by it (measured, not estimated):** `time`, `logd`, `bootlog`,
`display`, `console`, `shell`, `example` — seven of the eight services that
reach the syscall surface at all. Today they are green natively only because
`host_shim.c` substitutes `clock_gettime`. That substitution is exactly what
cannot ship.

**Cost of the wrong version.** If ticks are wall-clock (NTP-adjusted) instead of
monotonic, every elapsed-time computation in the corpus can go negative on a
clock step, and every one of those is a `while` loop.

**Failure it must not have.** Returning 0 on a bad read. A zero from a clock is
indistinguishable from a very fast machine, so the loop exits at once and the
caller reports success. If it cannot read, it must not return (see P6).

---

## P2 — `sys_net_send` / `sys_net_recv`: the link layer

```goose
extern fn sys_net_send(link: i64, frame: const u8[:])  -> i64 = "sys_net_send";
extern fn sys_net_recv(link: i64, out: u8[..1514]&)    -> i64 = "sys_net_recv";
```

**Shapes.** `int64_t sys_net_send(int64_t link, sl_u8 frame)` and
`int64_t sys_net_recv(int64_t link, r_l1514_u8 out)`. The 1514 is the contract:
an Ethernet frame with a 1500-byte MTU and no jumbo. The buffer is the caller's
and the callee may not exceed it.

**Returns.** Bytes sent / bytes received (0 = nothing this poll, not EOF).
Negative = error.

**Why two numbers and not one blocking read.** `sys_read_key` already sets the
precedent: `false` means "nothing this time" and the caller polls with
`sys_yield`. A blocking `recv` with no timeout primitive means one bad link
wedges the service that owns it.

**Blocked by it:** the whole protocol pack (`services/net/`, `socket`,
`sockets`, `netcfg`, `dhcp`, `dns`) — twelve modules carrying 89 + 45 native
checks today. Those checks prove the packet builders and parsers against a
loopback harness in `tests/harness/link.goose`, not against a NIC, and the
report says so.

**Open question the proposal must answer, not defer:** whether `link` is a
kernel handle or an index the kernel resolves per call. A handle means the
kernel must validate it on every call (cheap, safe). An index means a service
can address a link it was never granted — that is a capability question, and
the answer belongs in the ruling, not in the driver.

---

## P3 — `sys_spawn` / `sys_kill`: process lifecycle

```goose
extern fn sys_spawn(image: i64, len: i64, priority: i64) -> i64 = "sys_spawn";
extern fn sys_kill(pid: i64) -> i32                            = "sys_kill";
```

**Status: commented out in `services/supervisor/supervisor.goose`, not declared.**
That is deliberate. The supervisor's entire state machine — 53 native checks:
start, stop, crash, restart with backoff, give-up after three attempts — is
proven *as a state machine* without them. What is not proven is that a
transition moves real bytes into a real address space.

**Why this is a proposal and not a port.** Spawning needs three decisions the
freeze does not contain: where the image lives (the storage service's block
range? a kernel-owned region?), who owns the child's memory (the kernel, since
services have no `mmap`), and what `priority` means when K2's scheduler is still
round-robin. Writing the declaration before those are ruled would produce a
signature that has to change, which is worse than a comment.

**What the supervisor needs, minimally:** spawn returns a pid > 0 or a negative
code; the child's exit is observable to the parent (today the supervisor has
`sup_on_exit(pid, code)` and no producer for it); kill is idempotent for a pid
that has already exited.

**Blocked by it:** nothing that runs today. This is the one proposal whose
absence costs no green check — which is why it is third, not first.

---

## P3a — the exact numbers, if P3 is ruled yes (2026-11-02)

P3 above says *why* spawn needs a ruling before a declaration. This section says what the
numbers would be, so the ruling is a yes/no on a concrete ABI instead of a design session.
Nothing here is declared in `services/`; every line below is a **request**.

### The ask, in numbers

| slot | name | direction |
|---|---|---|
| 6 | `sys_spawn` | request |
| 7 | `sys_kill` | request |
| 8 | `sys_wait` | request |
| 9 | `sys_pid` | request — this is P5, promoted to a number |

Four slots out of the ten reserved (6–15), leaving 10–15 for the eleven services still
outside the freeze. Taking 8 and 9 is the part worth arguing: spawn alone gives the
supervisor a pid it cannot observe and cannot name itself with.

### The shapes

```goose
// 6 — start an image. Returns pid > 0, or a negative code. No partial success.
extern fn sys_spawn(image: i64, len: i64, priority: i64) -> i64 = "sys_spawn";

// 7 — stop a process. Idempotent for a pid that has already exited.
extern fn sys_kill(pid: i64, sig: i64) -> i64 = "sys_kill";

// 8 — collect an exit. Blocks up to timeout_ms; (pid, code) or (0, E_TIMEOUT).
extern fn sys_wait(timeout_ms: i64) -> i64, i64 = "sys_wait";

// 9 — who am I. No buffer, no failure, never 0 for a running process.
extern fn sys_pid() -> i64 = "sys_pid";
```

`image` is a storage block id plus `len` bytes, not a path: there is no filesystem in the
K2 kernel and a path would be a promise the kernel cannot keep. `priority` is 0..3 for
K2's four run queues; anything else is `E_INVAL` rather than a clamp, because a clamped
priority is a scheduler policy nobody voted for.

### The contract the supervisor already assumes

- Spawn is all-or-nothing: pid > 0 means the image is mapped and the entry point is
  scheduled. There is no "started but not runnable".
- `sys_kill` on an exited pid returns `CODE_OK`, not `E_NOTFOUND`. The supervisor's
  `sup_walk_stopped` retries kills and would otherwise report a false failure.
- `sys_wait` is the *only* producer for `sup_on_exit(pid, clean, uptime_ms)`. Today that
  function has no caller outside tests, which is the largest unproven seam in the
  supervisor: 117 checks prove the state machine, none prove a transition moves a process.
- `sys_pid` never returns 0 for a running process, so 0 is usable as "unknown" in an
  audit record.

### What each costs if refused

| slot | refused means |
|---|---|
| 6 | the supervisor is a rehearsal, not a supervisor; no service starts |
| 7 | no stop path at all; a wedged service is a wedged machine |
| 8 | restarts are counted but never observed; the budget is bookkeeping |
| 9 | `actor` in the audit log stays caller-supplied, and a crash report cannot name itself |

The four are separable on purpose: 6+7 make a supervisor, 8 makes its restarts real, and 9
is independence from the caller's honesty. If only one pair can be ruled today, rule 6+7
and leave 8+9 to the next window — the supervisor degrades to "starts things, cannot see
them exit", which is what it is today, but with a real process on the other end.

### What this does not ask for

No `mmap`, no `open`, no `fork`, no signals beyond the two the supervisor needs (0 = stop
now, 1 = stop after the current handler returns). Those are K3/K4 decisions and writing
their numbers now would freeze a design that has not been argued.

---

## P4 — a sleep that is not a spin

```goose
extern fn sys_sleep_ms(ms: i64) -> i64 = "sys_sleep_ms";
```

**The freeze already has 2 = sleep.** This is not a new number; it is the
observation that **nothing in `services/` calls 2**, because `sys.goose` never
declared it. The corpus polls `sys_ticks` + `sys_yield` instead. Under a
preemptive scheduler that is merely wasteful; on a single core it means a
sleeping service is a runnable service, and the log flush loop burns a core to
wait 10 ms.

**Proposal:** declare 2 as `sys_sleep_ms(ms) -> i64`, returning the number of
milliseconds actually slept (a signal can shorten it), and leave every existing
`while` loop alone. The loops are correct; they are just expensive. Changing
them is a follow-up, not a condition of the ruling.

---

## P5 — `sys_pid`: who am I

**Freeze slot 3.** Undeclared in `sys.goose`; nothing calls it. The supervisor
registers services by name and hands back a slot handle (`sup_register`), so it
can say which *entry in its table* is running — but no service can learn its own
process id, and nothing can ask whether the pid in a crash report is still the
process it names. Cheap to rule, cheap to implement, and the audit service wants it
(the `actor` field is currently whatever the caller passed in).

---

## P6 — what the kernel does when a syscall cannot be served

Not a number. **A gap in the freeze that all five above inherit.**

Today the contract is "negative return code", and `common/err` defines the
codes. What is missing is the case where the kernel cannot return at all: a
faulting user pointer, a dead UART. `sys.goose` says a dead UART must be visible
to the log service rather than silently swallowed — good — but a service that
gets `-E_IO` from `sys_write_serial` in its log path has nowhere to report it,
because reporting goes through the same call.

**Proposal:** rule that a failed `sys_write_serial` is (a) counted by the
kernel, (b) visible in a kernel-owned counter the shell can print, and (c) never
a reason for the kernel to kill the caller. Without this, a log outage is
indistinguishable from a quiet system, and the demo has no way to say
"this line is missing because the UART died".

---

## Summary for the ruling

| # | asks for | blocks | cost of no |
|---|---|---|---|
| P1 | reserved slot, `sys_ticks` | 7 services, every wait loop | no service can wait |
| P2 | 2 reserved slots, net pair | protocol pack, 134 checks | no network, honestly |
| P3 | 2 reserved slots, spawn/kill | supervisor's proof of effect | state machine only |
| P4 | existing slot 2, declared | CPU waste, not correctness | works, spins |
| P5 | existing slot 3, declared | self-identification in audit | services pass a name |
| P6 | a rule, not a number | log outage is invisible | silent failure |

**Nothing in this document allocates a number, and no file in `services/`
declares any of P1–P3 or P5.** They are comments and prose until Pax rules.
