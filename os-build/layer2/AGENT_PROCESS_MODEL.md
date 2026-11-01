# Layer 2 — the agent process model (Milo, ML-L2-01)

Status: **DRAFT** — first version 2026-11-01, target status DESIGNED
per `MILO_LAYER2_TASKS.md` (ML-L2-01). Nothing here is built: the
model is designed now, and no agent process runs until K6 exists
(KERNEL_SPEC.md K6: system calls, first userspace program, the Goose
services layer gets its first process). This document fixes what an
agent process IS on Meta OS, so Hana's Layer 2 shell work and Buffy's
Layer 1 service contract are written against the same model. Items
the kernel or the Mac build must answer are marked OPEN and are not
guessed here. Rules that bind this document: NO MOCKS anywhere; the
audit trail is part of the model, not an add-on; status words are
used exactly (DESIGNED / WRITTEN / COMPILED / VERIFIED / NOT BUILT /
BLOCKED, per `os-build/LAYERS.md`).

Sources this version is grounded in (all read on main 91dbbf5):
`os-build/LAYERS.md`, `MILO_LAYER2_TASKS.md`,
`os-build/layer1/K6_SERVICE_SHAPE.md` (DESIGNED, Pax), the K1/K2/K3
kernel state on main (K1 crate UNCOMPILED, Mac boot proof
outstanding; K2 framebuffer and K3 interrupts merged unwired at
6c29370b; R5 wiring BLOCKED on the K1 boot log and the absent
kernel/Cargo.lock). Lobster-side idioms are grounded in §6 from
a live lobster-mcp 1.1.0 check (2026-11-01), not asserted from
memory; Q1/Q5/Q9 and enforcement/storage stay OPEN.

## 1. What an agent process is

An agent process is a Layer 2 userspace process that acts on behalf
of a named principal (a person, or another agent process acting under
delegation) and does its work exclusively by calling Layer 1
services. It is not a kernel task with special privilege, not a
service, and not a shell: the shell (Hana's Layer 2 work) lists and
starts agent processes and reads real OS state; it does not grant
them anything the model does not.

An agent process has exactly four aspects, and a design that omits
one of them is incomplete:

1. **Identity** (§2) — who it is, who it acts for, where it came from.
2. **Lifecycle** (§3) — how it starts, stops, and fails.
3. **Capabilities** (§4) — what it is allowed to call, and nothing else.
4. **Records** (§5) — every action logged, in a form a human can audit.

## 2. Identity

- **Agent id.** A stable identifier assigned at start, unique among
  live agent processes. The id is what records cite (§5); a display
  name is never a substitute for the id in a record.
- **Principal.** The person (or delegating agent process) the agent
  acts for. Delegation chains are recorded, not flattened: a record
  cites the acting agent and the principal it acted for.
- **Origin.** Which Layer 2 program started it (shell command, app,
  or another agent process), and the start request that created it.
  An agent process with no recorded origin is not started.
- **No kernel identity beyond the task.** At K6 the kernel knows a
  service only as a task it loads (K6 shape item 1: one compiled
  binary, loaded as a K5 task). An agent process likewise carries no
  kernel-side privilege, role, or identity beyond its task; all
  agent identity lives in Layer 2 records and in the capability set
  checked at start (§4). OPEN: whether the kernel task id and the
  Layer 2 agent id are the same value or mapped — decided at R5/K6
  wiring time, not before, because it depends on the resolved
  bootloader and task shape (Q1/Q5 in `kernel/MAC_QUESTIONS.md`).

## 3. Lifecycle

States, in order: **defined** (a start request exists and names an
identity, a capability set, and an origin) → **starting** (the
kernel has accepted the task; BootInfo-style start data, if any,
has been handed over) → **running** → **stopped** or **failed**.
There is no other state, and no state is skipped in a record.

- **Start** passes the agent its identity, its capability set, and
  its origin record, the way K6 start passes a service its BootInfo
  block (K6 shape item 2). OPEN: the register/location convention
  for that handover — the same OPEN item as K6 shape item 2, set at
  R5/K6 wiring time.
- **Stop** is clean exit: the agent finishes its work, its final
  record is written, and its task ends. A stopped agent is not
  restarted implicitly; a new start request creates a new agent
  process with a new id.
- **Fail** is final at this layer, mirroring K6 shape item 5
  ("failure is final at K6"): an agent that faults or exits
  abnormally is logged with its name and exit state, and its task
  ends. No restart policy exists in this version — a restart policy
  is future work and will be designed, not assumed. This is
  deliberate: an agent that restarts itself without a new start
  request would break the audit trail (§5), because the new run
  would not have a recorded origin.
- **No suspend/resume in v0.** A paused agent process is not in
  this version; if one is needed later, it gets its own design
  section, not an implied state.

## 4. Capabilities

- **Agents call Layer 1 services only.** An agent process never
  calls the kernel directly and never touches hardware. Every effect
  an agent has on the system goes through a Layer 1 service call.
  This is the hard boundary of the model: anything that looks like
  a direct kernel access from an agent is a design violation, not a
  shortcut.
- **A capability is a named set of Layer 1 service calls.** The set
  is fixed at start, named in the start request, and recorded with
  the agent's identity. An agent that calls outside its set is
  failed ( §3), and the failed call is recorded.
- **No agent-to-agent channel in v0.** K6 shape item 4 sets "no
  service-to-service IPC at K6"; the agent layer inherits the same
  restraint: agents do not talk to each other directly in v0. An
  agent that needs another agent's work starts it (or asks the
  shell/principal to start it) through a recorded start request, so
  the delegation chain (§2) stays visible. Richer agent-to-agent
  communication is a later design with its own document; it is not
  implied by this one.
- **No capability is granted by the shell alone.** Hana's shell
  starts agent processes and reads OS state; it does not widen a
  capability set. Widening a set is a new start request with a new
  id and a new record.
- OPEN: how the capability set is enforced — a kernel-side table
  checked on each call, or a service-side check at the Layer 1
  boundary. This depends on the K6 syscall surface (six draft
  calls: exit, write_serial, write_console, read_key, ticks, yield)
  and on the Q9 handler-ABI answer, so it is left OPEN here.

## 5. Records (the audit trail)

Every agent action is logged. The audit trail is part of the model,
not an add-on, and a run with missing records is not a valid run.

- **One record per action.** A record cites: the agent id, the
  principal, the Layer 1 service called, the arguments that matter
  for audit (not bulk data), the result, and the tick at which it
  happened (K6 syscall 4, ticks, is the clock this layer has).
- **Failure records are mandatory.** A fault, an out-of-capability
  call, and an abnormal exit are each recorded with the agent's
  name and exit state, mirroring K6 shape item 5's serial logging
  for failed services. At minimum the record reaches serial; where
  the durable store lives (and how it rotates) is OPEN until a
  Layer 1 storage service exists.
- **Records are append-only in v0.** No record is edited or
  deleted by an agent process. Correction, if ever allowed, is a
  separate design with its own document.
- **A human can read the trail.** Records are plain, ordered, and
  cite ids a human can follow back to a start request. A trail that
  needs a special tool to be legible is not finished.

## 6. Lobster expression (grounded 2026-11-01, live check)

Grounded in a live `lobster-mcp` 1.1.0 stdio check run on this
VM 2026-11-01 (server reports Lobster source
github.com/aardappel/lobster @ 6c1389c6e2, 187 sections, 879
builtins). The committed gateway config at `mcp-gateway/`
points at a `_del` path that does not exist on this VM; the
check ran the same server from its actual local path
`mcp-servers/lobster-mcp/dist/index.js`. The Lobster toolchain
binary itself is NOT FOUND on this VM (`toolchain_status`), so
no Lobster code was compiled or run here: what follows is a
design mapping, not a verified program, which is consistent
with §7 — no agent-process code exists until K6 exists.

Lobster's concurrency model, verbatim in substance from the
docs (`language_reference#45` Multi-threading,
`language_spec#67` Threads): Lobster runs one VM per hardware
thread, each an independent and isolated copy of the program,
with no shared memory or VM state; communication and
synchronisation are explicit, through a "tuple space" (a bag of
Lobster objects used as messages) which are copied, not
shared. Worker builtins (from `search_builtins "thread"`,
10 matches): `start_worker_threads(numthreads)`,
`stop_worker_threads()`, `workers_alive()`,
`is_worker_thread()`, `thread_write(object)`,
`thread_read(type)`, `thread_check(type)`,
`thread_wake(type)`, `thread_information()`.

Mapping to §§2–5, and where the mapping stops:

- **Identity (§2): a worker thread is NOT an agent process.**
  A worker thread is the execution vehicle: a copy of the
  program running in isolation. The agent id, principal, and
  origin live in Layer 2 records (§2), not in the thread. Code
  can tell it is running as a worker via `is_worker_thread()`,
  but that answers "am I a worker", never "which agent am I":
  the agent id comes from the start request, as §2 requires.
- **Lifecycle (§3): start and cooperative stop map cleanly.**
  `start_worker_threads` is the start vehicle;
  `stop_worker_threads` makes `workers_alive()` false inside
  the workers, which should then exit — a cooperative clean
  stop, matching §3's stop. There is no Lobster construct for
  §3's failure rule: that a faulted agent ends finally with a
  logged name and exit state is a model rule imposed by this
  document and by K6 shape item 5, not a Lobster guarantee,
  and the K6 failure path must supply it.
- **Capabilities (§4): isolation is mechanical, enforcement is
  not Lobster's.** No shared memory means an agent process
  cannot reach another process's state at all: its only effects
  are objects it copies out through `thread_write`. That is
  the mechanism shape of "Layer 1 services only". But no
  Lobster construct enforces a capability set: the set is a
  Layer 2 record checked at the Layer 1 boundary, still OPEN
  per §4. And one tension is explicit: Lobster's queue is a
  general message channel, while §4 forbids agent-to-agent
  channels in v0. Resolution: on Meta OS the queue's
  legitimate v0 endpoints are Layer 1 services and the record
  store, not other agents. The queue mechanism is adopted;
  the agent-to-agent use is not.
- **Records (§5): copy semantics support append-only.** A
  record written with `thread_write` is a copied object: the
  stored record is a snapshot the sending agent can no longer
  mutate, which is exactly what §5's append-only rule needs
  on the sender side. The store side (durability, rotation)
  is still OPEN until a Layer 1 storage service exists.
- **Not claimed:** coroutine behaviour (the docs mention
  coroutines only historically, `philosophy#4`), sample
  `threads.lobster` behaviour (not run: no toolchain), and
  any Lobster construct beyond the builtins and sections
  cited above.

## 7. What this version does NOT claim (OPEN items)

1. **Lobster idioms beyond §6.** §6 is the grounded Lobster
   section (live lobster-mcp 1.1.0 check, 2026-11-01). Nothing
   in this document depends on a Lobster claim outside §6;
   coroutine behaviour, `threads.lobster` sample behaviour, and
   any construct not cited in §6 remain unclaimed until a
   toolchain run verifies them.
2. **K6 wiring answers** (Q1/Q5 bootloader and task shape, Q9
   handler ABI, syscall transport): all OPEN, owned by Rowan's
   Layer 0 work and the Mac build, listed in
   `kernel/MAC_QUESTIONS.md`.
3. **Capability enforcement point** (§4) and **record storage**
   (§5): OPEN until the first Layer 1 services exist.
4. **Restart policy, suspend/resume, agent-to-agent channels:**
   future designs, not implied here.
5. **Shell alignment:** Hana's Layer 2 shell work reads real OS
   state only (per `HANA_LAYER2_TASKS.md`); the shell's view of an
   agent process (list, start, stop) must match §§2–3 exactly, and
   any mismatch is a design conflict to resolve in the open, not
   by either side drifting.

## 8. Status path

DRAFT → DESIGNED once: (a) the Lobster section is grounded in a
live `lobster__*` check — DONE in §6 (2026-11-01 live check),
(b) Pax has reviewed it against the K6 shape — PENDING, and
(c) Hana confirms the shell's view matches §§2–3 — PENDING.
Status stays DRAFT until (b) and (c) land. It becomes WRITTEN
only when the first agent-process code exists, and no code
exists until K6 exists. Gate-1 for this branch is Milo's
standing duty, and merges go through Pax.
