# Layer boundary notes — Layer 4 (Goose services) and its neighbours

Who this is for: **Rowan and OpenCode** (Layers 1–3, the kernel) — what this
layer needs from you. **Milo** (Layer 5, agent runtime) and **Hana** (Layer 6,
shell and apps) — what this layer offers you. **Pax** merges against this sheet.

Every line is marked:

- **CONTRACT** — decided here, and other layers can build on it.
- **REQUIREMENT** — not built anywhere; the other layer has to do it.
- **OPEN** — nobody has decided, and work that assumes an answer is guessing.

Nothing in this document is COMPILED evidence. The Goose toolchain is
`NOT FOUND` on this machine and `kernel/src/main.rs` is still the K1 skeleton,
so both sides of every boundary below are paper.

## 1. What Layer 4 needs from Layers 1–3

| # | Item | Kind | Detail | Milestone |
|---|---|---|---|---|
| A1 | C-ABI call into a Goose `export fn` with one pointer, `i32` back | REQUIREMENT | `SERVICE_CONTRACT.md` §2. The entry is `export "svc_entry" fn service_main(...) -> i32`. Kernel calls it once; the return value is the process's exit code. | K6 |
| A2 | `write_serial(s, len) -> bytes written or negative` | REQUIREMENT | Used by `bootlog`. Negative is an error the service must be able to see; a clamp-to-zero return would hide a dead port. | K1 (`main.rs` has a serial path) |
| A3 | `write_console(s, len) -> bytes written or negative` | REQUIREMENT | Separate from serial on purpose: the console can be broken while the log still works, and the layer must survive that. | K2 |
| A4 | `read_key(out) -> bool`, distinguishing "no key" from "key" | REQUIREMENT + OPEN | The six-call K6 shape has `read_key` but no `wait_key`. Polling is what the layer can do. **Q-B-L1-1:** if the kernel can block a service until a key arrives, the console stops burning CPU. | K3/K6 |
| A5 | `ticks() -> i64`, monotonic, cheap to call | REQUIREMENT | Polled by `time`'s sleep loop. A tick that costs more than a few cycles makes every sleep in the layer expensive. | K3 |
| A6 | `yield()` that actually reschedules | REQUIREMENT | A no-op `yield` turns every sleep in the layer into a hard spin. This is the single highest-value kernel call for this layer. | K5 |
| A7 | BootInfo block, read-only, exact layout | REQUIREMENT + CONTRACT | Field-for-field with B-L1-08: framebuffer info mirroring K2's `FramebufferInfo`, memory summary, tick rate. Services read, never write. | K2/K6 |
| A8 | Message send that fails at the sender | REQUIREMENT | A silently dropped message makes every service above it unreliable and untestable. Failure must be a code the caller sees. | K6+ |
| A9 | Read a process's exit code and fault reason | REQUIREMENT | The supervisor's restart policy depends on telling a clean stop from a crash. | K6 |
| A10 | Per-process static storage with a documented limit | REQUIREMENT | Goose services allocate nothing at run time, so the linker must be able to say how much each service gets, and the kernel must grant it. | K4/K6 |

**The transport is OPEN (Q9).** `sys.goose` declares six calls; how they reach
the kernel (interrupt, syscall instruction, capability call, shared page) is not
decided here and this layer asserts nothing about it. Any kernel design that
keeps A1–A10 true is compatible with this layer.

**A note on A2/A3 that will save a kernel argument.** The layer asked for
`write_serial` to return a byte count rather than a status because the log needs
to know if a write was partial. If the kernel returns a status instead, that is
fine — but then partial writes are impossible and the kernel must guarantee it,
in writing, or `bootlog` is lying.

## 2. What Layer 4 offers Layers 5–6

| # | Offer | Kind | Who it is for | State |
|---|---|---|---|---|
| B1 | `bootlog`: an append-only boot record, one record per syscall | CONTRACT | anyone diagnosing a boot | WRITTEN (no ring retention yet) |
| B2 | `time`: monotonic clock, `sleep_ms`, one rate constant | CONTRACT | every service and every agent | WRITTEN (core only; no IPC handler) |
| B3 | One record format: `<ticks> <tag> <level> <message>` | CONTRACT | `logd`, the shell, the audit trail | WRITTEN in `bootlog`, formalised by B-L1-28 |
| B4 | A name registry so nothing hardcodes a service id | CONTRACT | Hana's shell, Milo's agent host | NOT BUILT (B-L1-22) |
| B5 | A supervisor that starts services in dependency order and restarts them per policy | CONTRACT | anything that assumes its dependency is up | NOT BUILT (B-L1-20/21) |
| B6 | An audit trail of what agents did, readable by the user | CONTRACT (the OS's promise) | Milo, and the user | NOT BUILT (B-L1-41/42) |
| B7 | Agent lifecycle: spawn, grant, quota, stop | CONTRACT | Milo | NOT BUILT (B-L1-38..40, 116) |
| B8 | Filesystem above the storage contract | CONTRACT | Hana's shell, every program | NOT BUILT (B-L1-79..84) |
| B9 | A shell with builtins and scripts | CONTRACT | the user and the agent's command surface | NOT BUILT (B-L1-87..92) |

**What Layers 5–6 must not do:** reach past this layer to the raw kernel. The
current that flows is L6 → L4 → L1–3, and a shell that calls syscalls directly
makes the audit trail a lie. That is a rule for Hana and Milo, and it is one
line in the merge gate.

## 3. Open questions that block Layer 4 work

| Q | Question | Blocks | Who can answer |
|---|---|---|---|
| Q-B-L1-1 | Is there a blocking key wait, or is polling the contract? | console efficiency, B-L1-17 | Rowan/Pax |
| Q-B-L1-2 | IPC message header: fixed here as sender/kind/length/correlation, but the transport underneath is undecided | every service that talks to another, from B-L1-20 on | Pax + Rowan |
| Q-B-L1-3 | Will the kernel ever implement `gs_os_*`, so Goose's own `os` module works unchanged? | if yes, much of this layer's file and process work becomes stdlib | Pax |
| Q-B-L1-4 | BootInfo delivery: argument pointer, fixed address, or a syscall the service makes? | A7, B-L1-08 | Rowan |
| Q5 | Goose freestanding link: can Goose-generated C link with no libc? | everything past WRITTEN, B-L1-75 | anyone with a toolchain |

## 4. What this sheet does not claim

- It does not claim a single line of Layer 4 runs.
- It does not claim the kernel implements any of A1–A10. All ten are requests.
- It does not settle Q9, and it deliberately leaves the six syscall signatures
  as *our* request rather than a mirror of a kernel design that does not exist.
