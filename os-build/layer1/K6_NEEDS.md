# K6 needs — what Layer 4 is waiting for (B-L1-66)

Hand-off for **Rowan / OpenCode**. These are the exact points, not vibes. Each
one names the file and function in this layer that is blocked on it, so the
kernel side can answer "already there / planned at Kx / will not do" and this
layer can change the code instead of the question.

Status: every answer column is empty. Nothing here is COMPILED. The Goose
toolchain is still `NOT FOUND` on this machine, so even the answers would not
raise a status word today — but they unblock the code.

Format matches `kernel/MAC_QUESTIONS.md`: question, the code it blocks, the
answer shape that would close it.

## A. The six syscalls (`services/common/sys/sys.goose`)

The layer declared six external calls. All six are `extern` — unimplemented
here, expected from the kernel side.

| # | Question | Blocks | Answer that closes it |
|---|---|---|---|
| Q-B-L1-1 | What is the calling convention for `svc_entry`? We assumed C ABI, one pointer argument, `i32` return (`SERVICE_CONTRACT.md` §2). | every service's entry point | the exact ABI: argument registers, who cleans the stack, whether a return value is the exit code |
| Q-B-L1-2 | `write_serial(s, len)`: does it return **bytes written** (can be partial) or a **status**? `bootlog` distinguishes them. | `bootlog`, `logfmt`, `logd` | one line of the signature, and if it is a status, a written guarantee that short writes are impossible |
| Q-B-L1-3 | `write_console(s, len)`: same question, and **is it allowed to fail** while serial still works? The design assumes yes. | `console`, `display`, `shell` | yes/no, plus the failure code |
| Q-B-L1-4 | `read_key(out)`: does `false` mean "no key right now" or "error"? We assumed "no key", with errors being a separate, later call. | `input`, `shell` | the semantics of the bool |
| Q-B-L1-5 | Is there a **blocking** key wait in K6? Polling `read_key` in a loop is what the layer does now. If the kernel can block, `console` stops burning a core. | `console`, `shell`, `session` | yes/no; if yes, the call |
| Q-B-L1-6 | `ticks()`: **rate**, **width** (we assumed `i64`), and **does it reset**? Wrap behaviour decides whether `time` compares with subtraction or masks. | `time`, `watchdog`, `dhcp`, `dns`, `socket`, `updater` | rate in Hz, type, and wrap rule |
| Q-B-L1-7 | `yield()`: is it a real reschedule, or a hint that may be a no-op? A no-op turns every `sleep_ms` into a spin. | `time.sleep_ms` and everything above it | which, and if real, the minimum guaranteed behaviour |
| Q-B-L1-8 | `exit(code)`: does it **not return**? `updater` and the test programs call it in the last statement on purpose. | all tests, `updater` | confirm no-return, or the return value that means "not exited" |

## B. Memory (`services/common/boot/boot.goose`)

| # | Question | Blocks | Answer that closes it |
|---|---|---|---|
| Q-B-L1-9 | Per-process static storage: **how much**, and who decides? Goose services allocate nothing at run time, so the number is a linker/loader constant. | every service; the fixed buffer sizes in `services/MANIFEST.md` | a number, and whether it is per service or a shared arena |
| Q-B-L1-10 | Is that storage **zeroed** at start? `ring`, `bootlog` and the registry assume zeroed slots. If not, they must clear explicitly — cheap, but it must be known. | `bootlog`, `ring`, `registry`, `audit` | yes/no |
| Q-B-L1-11 | **BootInfo delivery**: argument pointer (A1), fixed address, or a syscall the service makes? B-L1-08 declares a struct; nothing says how it arrives. | `boot`, every service's first line | which of the three |
| Q-B-L1-12 | Can a service **share** a page read-only with another service (for the call matrix, the service table)? Without it, `callmatrix` and `registry` are copied per process and drift. | `callmatrix`, `registry`, `session` | yes/no; if yes, the call shape |

## C. Scheduling and process facts

| # | Question | Blocks | Answer that closes it |
|---|---|---|---|
| Q-B-L1-13 | **Exit code + fault reason**: can the supervisor read both? It restarts a clean stop differently from a crash (`sup_decide`). | `supervisor`, `watchdog` | the two calls, or confirmation that only one exists |
| Q-B-L1-14 | **Kill**: is there a call to stop another process, or does the supervisor ask a service to stop and trust it? The design says the supervisor asks, and the kernel kills only on timeout. | `supervisor`, `watchdog` | which exists |
| Q-B-L1-15 | **Timeouts**: can the kernel tell a service was descheduled for 500 ms? The watchdog measures wall ticks and will false-positive on a busy machine if it cannot. | `watchdog` | yes/no |
| Q-B-L1-16 | **Signals**: does an interrupt handler run in the interrupted process's context or a kernel thread? `input` assumes its handler only enqueues and never allocates. | `input`, `devices` | which |

## D. Transport (still Q9, unanswered)

| # | Question | Blocks | Answer that closes it |
|---|---|---|---|
| Q-B-L1-17 | **What carries a message?** Interrupt, `syscall` instruction, capability call, shared ring. The layer asserts nothing about transport, but it does assume **send failures are visible to the sender** (A8). | `supervisor` ↔ services, `agenthost` | the mechanism, plus the failure code |
| Q-B-L1-18 | **Message size limit.** The record format caps at 256 bytes; is that under the limit? | `logd`, `audit`, `agenthost` | a number |
| Q-B-L1-19 | **Ordering**: are two messages from one sender delivered in order? `audit`'s chain assumes yes; if not, it must carry sequence numbers (it currently does not). | `audit` | yes/no |
| Q-B-L1-20 | **Correlation**: does the transport return a reply token, or does the layer match on its own header field? Currently our own header. | every request/reply pair | which |

## E. Build and toolchain (not Rowan's, but it blocks the same work)

| # | Question | Owner | Why it blocks K6 |
|---|---|---|---|
| Q5 | Can Goose-generated C link **freestanding**, with no libc? | Pax / whoever lands the toolchain | if no, the entry point, the syscall stubs and the record format are all rewritten against a hosted runtime |
| Q6 | Does the K1 boot log path (`kernel/src/main.rs`) survive into a service binary, or is serial a kernel-only privilege? | Rowan | if kernel-only, every service's diagnostics go through `logd` from the first line, and `bootlog` cannot bootstrap |

## What would change in this layer, per answer

Written down now so the answers land as work rather than as a discussion:

- **Short writes impossible** (Q2/Q3 = status): delete the partial-write loops in
  `fmt.append_bytes` callers; three call sites, and `bootlog` loses its retry
  code, which is a simplification.
- **Blocking key wait exists** (Q5 yes): `console` keeps one loop instead of a
  poll-with-yield; `shell` gains a blocking prompt, and the CPU spin in the
  bottom of `input` goes away.
- **Ticks wrap at 32 bits** (Q6): every `a - b` comparison in `time`,
  `watchdog` and `updater` becomes a masked subtraction. That is a real change
  in three files and it must not be discovered by a boot that hangs after 49
  days.
- **Storage is not zeroed** (Q10): `ring_init`, `bootlog_init` and
  `registry_init` gain explicit clears. Cheap, but they are currently relying on
  a promise nobody made.
- **Shared read-only pages exist** (Q12): `callmatrix` becomes a pointer into
  one table instead of a per-process copy, and the drift class of bug disappears.

## Not asked, deliberately

- **Heap allocation.** The layer is built to not need it; asking would invite a
  design that depends on it.
- **Threads.** `goose run` cannot even place thread-local storage (see
  `LN-2` in `LANE_NOTES.md`), and services are single-threaded by contract.
- **Filesystem in the kernel.** The FS is a service (Wave G), on purpose.

Every question above is one Rowan can answer from `KERNEL_SPEC.md` plus the
implementation, or one Pax can rule on. None needs a meeting.
