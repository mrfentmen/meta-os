# K4 IPC — build step (build, not design)

**Assignment:** Pax K4 review (`os-build/K4_REVIEW_PAX.md` on main)
plus Pax bus order 2026-11-02 10:39 EST: "K4 build unblocked,
build from it." **Base:** origin/main `7cfb48d` at branch
creation (parent is the then-current main). **Status:** code,
not proof. Nothing here is booted: the gate pack in design §7
runs through OpenCode 1's Mac gate, read by Pax, exactly like
every kernel step before it. `syscalls.rs` is FROZEN (F1) and
untouched; the only numbers consumed are Pax-assigned 6/7.
K3's build is still unmerged, so the mapped-at-call-time
refusal rule stands (design §3/§5); if K3 lands first, its
build's rule governs and this build's rule is revisited then.

## 1. The 4 required changes, incorporated

1. **§6 peer-id mechanism fixed.** The design sketch's
   "talker `getpid`s the listener's id" was impossible
   (`getpid` returns the caller's own id) and is replaced by
   the real mechanism: peer ids are the fixed spawn-order ids
   from the gate build's loader table, published as named
   constants in the pair. Each program learns only its own id
   from `getpid`. The `ipc_send` argument description is
   corrected the same way.
2. **§4 squatting limitation named.** No sender filtering in
   step 1: any live task can occupy any live task's only slot
   (including the console's) until it receives or exits.
   Accepted knowingly; the later blocking-receive step must
   revisit it before IPC is offered to untrusted programs.
3. **Mailbox clearing on every removal path.** The clear
   lives inside `sched::exit_task`, the single funnel for all
   three removal paths in this kernel — voluntary exit
   (syscall 0), trampoline return, and the ring-3 fault kill
   (`page_fault_handler` calls `exit_task`). No path removes
   a task without passing through it, so no queued message
   can linger under a dead id, and Q-I3 slot reuse inherits
   nothing (`reap` still has no caller in K5).
4. **§7 literal gate log lines pinned.** Every send, receive,
   and refusal line is fixed verbatim in design §7, so the Mac
   boot log is checkable line-by-line, not readable only in
   hindsight.

## 2. What was built

- `kernel/src/sched.rs`: the mailbox home (Q-I2 answered) —
  parallel arrays alongside `SLEEPS` (`IPC_OCCUPIED` /
  `IPC_SENDER` / `IPC_LEN` / `IPC_BYTES`, one 64-byte box per
  row, kernel-owned static storage, no heap, no page
  sharing). `task_is_live` (row exists and state is not
  `Exited`; a sleeping task is live, id 0 never is),
  `ipc_queue` (re-checks liveness + box state at commit;
  the re-check cannot disagree with the dispatch pre-check
  because the handler runs straight-line on one CPU with no
  switch between them), `ipc_take` (empties the caller's box),
  and the `exit_task` clear (§1.3). `spawn_task` zeroes the
  new row's box. `MAX_TASKS` stays 8 (Pax Q-I1: swap, do not
  grow) — no table change in this branch.
- `kernel/src/user.rs`: dispatch entries 6 = `ipc_send` /
  7 = `ipc_recv` in the inline `match` only. `ipc_send` is
  the first three-argument syscall, so the length arrives via
  the existing `SAVED_RDX` constant (previously unused —
  this branch is what uses it). Validation order is design
  §3 verbatim: live destination, then mapped buffer +
  length `1..=64`, then box state; every refusal returns
  `u64::MAX` and changes no state. `ipc_recv` requires
  capacity `>= 72` (8-byte sender header + 64 payload, never
  truncated) and validates the 72-byte worst-case write
  region as mapped (the payload length is unknown until the
  box is taken, so the full region is checked up front);
  success copies sender id little-endian + payload into the
  caller's own buffer and returns `8 + payload_len`. The
  copy touches only the caller's validated buffer plus
  kernel storage — never a peer's pages — so the shared
  mapper root is not crossed, per the K3 precedent. Sender
  ids are kernel-filled from `current_id()`, never
  caller-supplied.
- `os-build/K4_IPC_DESIGN.md`: the 4 required changes above
  (§§4, 5, 6, 7, 8 updated; numbers now Pax-assigned, not a
  proposal). No other design content changed.
- NOT in this branch, by assignment: the talker/listener
  programs (Buffy's, R11-273 — the pair is written against
  design §6, not by Rowan), and the gate-build swap itself
  (the Mac/gate lane swaps two demo slots in `start_demo_tasks`
  and publishes the pair's spawn-order ids as the named
  constants; this branch changes no spawn order, so every
  existing id stays stable).

## 3. Gate pack for OpenCode 1 (design §7, unchanged in shape)

One boot, no panic, console task alive, third task
unaffected, log lines verbatim per design §7: exchange leg,
full-box refusal leg (second send refused, first message
received intact), empty-receive leg, dead-peer leg (send to
an exited id refused; message sent before its sender exits
still received with the dead sender's id), negative leg
(unmapped send buffer + undersized receive buffer refused,
no state changed, no task killed).

Gate failure modes that must NOT be papered over: an
exchange leg that passes via shared memory or a global
instead of the mailbox; any missing log line; a boot where
the third task dies or the console stops; any panic.

## 4. Verification done on this branch (stated exactly)

- `cargo check --target x86_64-unknown-none` on the kernel
  crate, run on this VM (cargo 1.99.1, `RUSTC_BOOTSTRAP=1`
  for the crate's build-std config): clean, 23 warnings
  (2 duplicates) — main's baseline on the same harness is 24
  (same 2 duplicates), and the delta is exactly the
  previously-unused `SAVED_RDX` constant, now used by the
  syscall-6 dispatch; zero warnings from this branch's code.
  The check used stand-in ELF bytes for `include_bytes!`
  (the real userspace ELFs are built by the Mac pipeline),
  so this is a type/syntax check, not a boot claim.
- NOT done here, owed by the Mac lane: Milo gate-1 on this
  branch, the Mac build with real ELFs, and the OpenCode 1
  QEMU boot log for §3. Pax merges only on that gate log.
- Fences: `syscalls.rs` untouched, no number beyond Pax's
  6/7 used, K3/K5/COW/swap untouched, no file under `os/os/`
  touched, nothing merged by this branch (branch only).
  `MAX_TASKS` unchanged at 8; no spawn order changed.
