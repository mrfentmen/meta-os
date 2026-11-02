# Layer 4 service contract

What a Goose system service **is** on Meta OS: how it starts, how it is named,
how it reaches the kernel, how services talk to each other, how one reports
health and failure, and how it stops.

Status: **DESIGNED**. No service is COMPILED — `goose__toolchain_status`
returns `Goose toolchain: NOT FOUND` on this machine (checked 2026-11-01), so
nothing here can be checked by a build. Every kernel assumption below is written
as a **requirement on Layers 1–3**, never as a fact about what the kernel does
today.

Grounding: every Goose language claim in this document was verified through the
`goose-mcp@1.1.0` server, which is bundled from `aardappel/goose` @ `b781587`.
The section ids are recorded next to each claim so a reviewer can re-run them.

## 1. What a service is

A service is a **single-threaded Goose program** that:

- is one directory under `services/<name>/`, per OS-165 and B-L1-07;
- is compiled to C and linked freestanding (Goose has no runtime of its own to
  speak of — see §3), with the kernel as its only dependency;
- owns a fixed amount of static storage and allocates nothing from a heap;
- never returns from its main loop except to stop.

Goose's memory model makes this natural rather than forced: threads share
nothing, there are no locks or atomics, and the language is designed around
arrays whose length is known to the compiler or carried in a slice. Verified:
`spec#50` ("Type-safe reuse and stale references") and `tutorial#21` ("Threads
that share nothing").

**Why single-threaded, and where the concurrency goes.** A service that wants
to do several things at once either (a) does them in sequence with bounded
work per step, or (b) is several services. The kernel's scheduler (K5) provides
the concurrency; the service does not reach for threads. This is a deliberate
cost: it keeps every service auditable, which is the point of an OS that hosts
agents.

## 2. How a service starts

Two options exist in Goose, and the contract picks one:

- `export fn` emits a C-callable wrapper — verified in `reference#108` and
  `spec#41`: *"An `export fn` defines a normal Goose function and emits a
  C-callable wrapper."*
- `extern fn` is the other direction, and is what the service uses to reach the
  kernel (§3).

**Contract:** a service exports exactly one entry symbol:

```goose
export "svc_entry" fn service_main(boot: BootInfo&) -> i32 {
    // ... service body ...
    return 0;
}
```

- The kernel (K6) enters at `svc_entry`, once, with a reference to the BootInfo
  block. A reference, not a copy: the block is read-only for the service.
- Returning from `service_main` ends the process with the returned code: `0` is
  a clean stop, anything else is a failure the supervisor records.
- **Requirement on Layers 1–3 (K6):** the kernel must be able to call a
  C-ABI symbol with one pointer argument and read an `i32` back, and it must lay
  the BootInfo block out exactly as B-L1-08 declares it. This is not proven; it
  is a requirement recorded for Rowan/Pax.

The older hosted entry (a `main` that the Goose runtime calls) is **not** used
here: it presumes a host process environment, which is exactly what our kernel
replaces.

## 3. The kernel boundary — and why the `os` stdlib is not it

Goose ships an `os` stdlib module with 25 functions, verified via
`goose__list_symbols_in_module("os")`:

```
read_file, write_file, write_file_atomic, append_file, file_exists,
delete_file, rename_file, make_dir, is_dir, delete_dir, list_dir,
read_line, read_stdin, write_stdout, write_stderr, flush_stdout,
arg_count, arg, args, env, trim_memory, resource_dir, time, clock,
time_ns, clock_ns, sleep, sleep_ms, random_seed
```

**This is the single most important fact for this layer, and it is a trap.**
Those functions are backed by C functions named `gs_os_*`, which per `spec#40`
are *"declared in `src/runtime/runtime_ext.h` and defined in
`src/runtime/runtime_os.h`"* — i.e. they are implemented by Goose's **host**
runtime against an existing operating system's file and process APIs. On Meta OS
there is no such host: `write_stdout` has nothing to write to, and `read_file`
has nothing to read from, until Layer 4 itself provides them.

So the layer's rule:

> **Services do not `import os`.** They bind to kernel syscalls through
> `services/common/sys.goose` (B-L1-09), which declares our own `extern fn`s.
> The `os` module becomes available again only if and when the kernel
> implements the `gs_os_*` surface itself — recorded as an open option, not a
> plan.

The extern form is verified in `spec#40`:

```goose
extern fn write_serial(s: const u8[:]) -> i64;
extern fn read_key(out: u8[>..]&) -> bool;
```

- A declaration without a body binds a Goose signature to a C function; the
  optional `= "symbol"` renames the C side. Without it, the Goose name is used.
- `const u8[:]` is a read-only slice (pointer plus count).
- `u8[>..]&` is a caller-supplied output buffer: the callee fills it and
  cannot grow it. This is the no-heap output idiom and it is what every
  formatting call in this layer uses.
- **Transport stays OPEN (question Q9).** These are *declarations*; how the
  call reaches the kernel (int 0x80, syscall instruction, a shared page, a
  capability call) is not asserted anywhere in this layer. B-L1-09 records the
  shim requirement and leaves the mechanism to the kernel designers.

### The six draft calls

From the K6 shape in the work order (B-L1-09): `exit`, `write_serial`,
`write_console`, `read_key`, `ticks`, `yield`. Their Goose signatures:

```goose
extern fn sys_exit(code: i32);
extern fn sys_write_serial(s: const u8[:]) -> i64;
extern fn sys_write_console(s: const u8[:]) -> i64;
extern fn sys_read_key(out: u8[>..]&) -> bool;
extern fn sys_ticks() -> i64;
extern fn sys_yield();
```

- `sys_write_serial` / `sys_write_console` return the count written, or a
  negative error code. They are separate calls because a service must be able
  to log when the console is broken and vice versa.
- `sys_read_key` returns `bool` — the trailing-bool convention (§5) — and fills
  the buffer with one key event. A `true` with an empty buffer means "no key
  pending" is **not** the contract; **requirement:** the kernel must distinguish
  "no input" from "input", so `false` means no key this call, and the caller may
  yield and ask again. This is flagged as **open question Q-B-L1-1** to Pax:
  the six-call shape has no `wait_key`, and polling is what we have until K6
  says otherwise.
- `sys_ticks` returns monotonic ticks; the rate is fixed by the kernel and
  published in BootInfo (B-L1-08), never assumed here.

## 4. Naming

- **Service name:** lowercase, one word where possible, `[a-z][a-z0-9_]*`, and
  it is the directory name in `services/`, the export prefix of its records, and
  the name the registry answers to.
- **Registry:** name → service id, owned by the `registry` service (B-L1-22).
  A service does not hardcode another service's id; it resolves a name once at
  start and fails loudly if the name is absent.
- **Record tag:** every log line carries the service name as its tag, so the
  single log sink (`logd`) can filter by origin without the sink knowing the
  service's internals.

## 5. How a service reports failure

Goose has no exceptions and no `Result` type. Verified in `samples/04_errors.goose`:
*"Goose has no exceptions and no Result type; it has three idioms: a trailing
bool (or code) for a two-outcome call, an optional for 'found or not', and
`return ... from` for a failure deep inside nested calls."*

**Contract — the layer uses exactly these, in this order of preference:**

1. **Trailing bool** for a call that either worked or did not:
   ```goose
   fn parse_age(s: u8[:]) -> i32, bool { ... }
   let v, ok = parse_age(input);
   if !ok { return 0, false; }
   ```
2. **Trailing error code** where the caller must distinguish failures:
   `-> T, Error` with `Error.ok` as the success value. The code set is
   B-L1-12's job; this document only fixes that a code, never a string, crosses
   a service boundary, and that `0` is success.
3. **Optional** (`T?`) for "found or not", narrowed with `if`/`guard` before
   use — never a nullable that the caller might forget, because Goose requires
   narrowing before you can touch the reference.
4. **`return … from`** to lift a failure out of nested parsing to the one place
   that handles it.
5. `assert` and `abort` are for programmer error and for a state the service
   cannot continue from. A service that hits one has failed, and the supervisor
   treats it as such.

**Failure is a record, not a silence.** A service that cannot do its job writes
one log record naming the failed operation and the code, then either degrades or
exits non-zero. A service that exits `0` after failing to start is a bug and is
gated against (B-L1-62 source audit).

## 6. How services talk to each other

**Open question Q9 territory.** The transport is not settled, and this document
does not settle it. What *is* fixed, because every service depends on it:

- Messages are **fixed-size**, described by a struct with no pointers into
  another process's memory. A message that contains a slice is a message that
  contains a pointer into someone else's address space, which the kernel will
  not honour, so slices inside messages are forbidden and the payload is
  `u8[..N]` with a length field.
- Every message has: sender service id, kind, length, and a correlation id for
  request/reply. The header is the same for every service; B-L1-29 and B-L1-33
  specialise the payload, not the header.
- **Requirement on Layers 1–3 (K6+):** a send that cannot be delivered must
  fail *at the sender* with a code, not silently drop. A silent drop makes every
  service above it unreliable and untestable.
- A service never blocks forever on a reply: every request carries a deadline in
  ticks, and a timed-out reply is an error code the caller handles.

## 7. Health and liveness

- A service **heartbeats** by writing one record per interval through `logd`.
  The interval comes from its config (B-L1-13), default 1 Hz.
- The supervisor (`supervisor`, B-L1-20/21) is the only component that restarts
  anything. Services do not restart themselves, and services do not restart each
  other.
- The watchdog (B-L1-23) watches for missing heartbeats and escalates to the
  supervisor with a code. Escalation is auditable: the `audit` service records
  it (B-L1-41).
- Health is **observable from outside the service**: the supervisor's table, the
  log, and the audit record. A service's own opinion of its health is a hint, not
  evidence.

## 8. How a service stops

- **Clean stop:** the supervisor sends a stop message; the service finishes the
  step it is in, flushes its log, and returns `0` from `service_main`.
- **Failure:** returns non-zero, or faults. The supervisor records which, and
  applies the restart policy for that service.
- **Shutdown of the OS:** services stop in reverse boot order (B-L1-64), and the
  log sink is the last thing to go quiet. That ordering is a requirement on the
  supervisor, not a hope.

## 9. Requirements this contract places on Layers 1–3

Collected here so Rowan/Pax can act on them without reading the whole document.
None of these are done; all are requirements.

| # | Requirement | Needed by | Milestone |
|---|---|---|---|
| R1 | C-ABI call into `export fn` with one pointer argument, `i32` returned | all services | K6 |
| R2 | BootInfo block laid out exactly as B-L1-08 declares, read-only to the service | all services | K2/K6 |
| R3 | `write_serial` and `write_console`, returning count or negative code | bootlog, console | K1/K2 |
| R4 | `read_key` that distinguishes "no key" from "key", with a defined event size | console, input | K3/K6 |
| R5 | Monotonic `ticks` with a published rate in BootInfo | time, every heartbeat | K3 |
| R6 | `yield` that actually returns the CPU to the scheduler | all polling loops | K5/K6 |
| R7 | Message delivery that fails at the sender rather than dropping | all IPC | K6+ |
| R8 | A way to read a service's exit code and fault reason | supervisor | K6 |
| R9 | Static storage per process with a documented limit (size audit, B-L1-136) | all services | K4/K6 |

## 10. What is verified, and what is not

**Verified through `goose__*` (2026-11-01):** the `extern fn` and `export fn`
forms including the `= "symbol"` rename (`spec#40`, `spec#41`, `reference#106`,
`reference#108`); the trailing-bool and optional error idioms and the absence of
exceptions/`Result` (`samples/04_errors.goose`, `samples/01_tour.goose`); the
`os` module's 25 symbols and their `gs_os_*` host-runtime backing (`spec#40`,
`list_symbols_in_module`); the 18 stdlib modules and their symbol counts; the
no-heap/no-shared-threads model (`spec#50`, `tutorial#21`).

**Not verified, and cannot be from this machine:** that any of this compiles —
there is no Goose toolchain (`toolchain_status` → `NOT FOUND`); that the six
syscall signatures match what the kernel will implement; that a freestanding
link of Goose-generated C against our kernel is possible at all. That last one
is the largest unknown in the layer and it is B-L1-75's job to find out.

**Open questions raised here:** Q-B-L1-1 (no `wait_key` in the six-call shape,
so polling with `yield`), Q-B-L1-2 (message header layout is fixed here but the
transport is not), Q-B-L1-3 (whether the kernel will ever implement `gs_os_*` so
Goose's own `os` module works unchanged).
