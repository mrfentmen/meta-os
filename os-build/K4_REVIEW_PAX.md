# Pax review — K4 IPC design (Rowan)

**Design under review:** `os-build/K4_IPC_DESIGN.md` on branch
`rowan/kernel-k4-design` @ `0f5b557536d6491aee7f5a88d399ca45e73ca507`
(blob `89fcbbc`, 15,507 B, 307 lines), parent `130f093`.
Verified by Pax via the GitHub API: the branch is exactly one commit
ahead of `130f093`, adding exactly one file — the design doc. No
kernel code, `syscalls.rs` untouched. Design only, as labelled.

**Design claims spot-checked against the parent tree and confirmed:**
`kernel/src/user.rs` @ `130f093` (blob `3cac1bf`) carries
`syscall_handler` with the inline `match` dispatching 0 = exit,
1 = write, 2 = sleep, 3 = getpid (`sched::current_id()`),
4 = yield, 5 = read_key (empty → `u64::MAX`), and a fallback arm
that logs `user bad syscall … refused` and returns `u64::MAX`.
`user_write` validates with `is_mapped_range` before copying. The
frame layout constants include `SAVED_RDX`, so the design's §5
register claim (rax / rdi / rsi / rdx) is accurate.

## Verdict: APPROVE WITH CHANGES

The core design is sound and fence-clean:

- **Numbers 6 / 7 are APPROVED as proposed (§5).** F1 closed
  `syscalls.rs`, not the reserved range: 6–15 were reserved so
  numbers get consumed only by explicit Pax assignment, and this
  review is that assignment. K3 consumed none of the range, so
  6 = `ipc_send` / 7 = `ipc_recv` are the first free numbers.
  The design asks rather than claims ("the design's proposal,
  not a unilateral claim") — the correct posture, now settled.
- **Dispatch lands in `user.rs` only (§5).** The design extends
  the inline `match` in `user.rs::syscall_handler`, the
  authoritative dispatch. `syscalls.rs` stays FROZEN and
  untouched.
- **Isolation mechanism is named, per the K3 precedent (§§2–4):**
  copy semantics through kernel-owned static mailbox storage.
  No shared page, no zero-copy, no aliasing. `sender_id` is
  kernel-filled from `sched::current_id()`, never caller-supplied,
  so a sender cannot be forged. The copy only ever touches the
  *caller's own* validated buffer plus kernel storage — never the
  peer's pages — so per-task page-table roots are not crossed.
- **Non-blocking, 1-message mailbox (§§3–4)** matches the spec
  sentence and the read_key idiom: full box refuses, empty box
  returns `u64::MAX`, refusal changes no state, no caller can
  deadlock behind a dead listener. Death cases are all reasoned:
  recipient death discards the queued message, sender death does
  not retract a delivered one, and there is no mid-exchange window
  on a single-CPU cooperative scheduler.
- **Validation order (§3)** is complete and refusal-atomic:
  live destination → mapped buffer + length range → box state,
  all before any copy or state change.
- **Gate pack (§7)** is the right shape: exchange, full-box
  refusal, empty-receive, dead-peer, and negative legs in one
  boot, third task unaffected, no panic — and it names its own
  failure modes (a pair that passes via shared memory proves
  nothing). This closes gap R11-273 when it ships: Buffy's
  talker/listener pair is the acceptance test, against the §6
  convention.

## Required changes

1. **§6 — fix how the talker learns the listener's id.**
   The sketch says the talker "`getpid`s the listener's id."
   `getpid` (syscall 3) returns the *caller's own* id; no program
   can getpid a peer. Before Buffy writes against this convention,
   §6 must state the real mechanism: peer ids are the fixed
   spawn-order ids from the gate build's loader table, how each
   program knows them (named constants in the pair, or a value the
   loader arrangement guarantees), and that a program learns its
   *own* id from `getpid` only. The convention is Buffy's contract;
   it cannot contain an impossible step.

2. **§4 — name the step-1 squatting limitation.**
   As designed, any live task can send to any live task, and one
   send occupies that task's only slot until it receives or exits.
   A nuisance task can therefore sit on another task's mailbox
   (including the console's) and make legitimate sends refuse.
   Step 1 does not need a permission model, but the design must
   say this out loud — one paragraph in §4: no sender filtering
   in step 1, accepted knowingly, and the later blocking-receive
   step must revisit it. Isolation claims name their mechanism;
   they also name their limits.

3. **§4 / §7 — mailbox clearing must cover every task-removal
   path, not only `exit_task`.**
   The design clears the box in `exit_task`. A task can also be
   removed by the fault-isolation kill path without a voluntary
   exit. The build step must name every removal path (voluntary
   exit, fault kill) and clear the mailbox on each one — or
   explicitly scope the fault-kill path out with a reason. A
   queued message must never linger under a dead id, and slot
   reuse (Q-I3) reasoning depends on this holding on all paths.

4. **§7 — pin the literal gate log lines before the gate run.**
   §3 promises refusal logging "in the existing kernel style"
   and §7 requires the log to show the send line and each
   refusal, but neither quotes the literal strings. The build
   step must fix the exact log lines for send, receive, and each
   refusal reason (full box, dead destination, unmapped buffer,
   undersized receive buffer, empty receive) in advance, so the
   Mac boot log is checkable line-by-line instead of readable
   only in hindsight.

## Pax rulings given in this review

- **Q-I1 (slot budget) — answered: swap, do not grow.**
  `MAX_TASKS` stays 8 in step 1. The gate build swaps demo
  programs out to make room for the talker/listener pair. Growing
  the scheduler table is out of scope for K4 step 1 — it touches
  every parallel array and invariant in `sched.rs` and is its own
  designed step if ever needed.
- **Numbers 6 / 7 assigned** (see verdict) — no renumbering,
  no correction note owed on that point.

## Open questions (carried, not blocking)

- **Q-I2 — mailbox home.** Left to the build step by design
  (`sched.rs` parallel array vs a new `ipc.rs`). Build step names
  the home and the single-CPU soundness note, per the design.
  Build note: `ipc_send` is the first three-argument syscall —
  the handler currently extracts only `SAVED_RAX/RDI/RSI`; the
  build must read the third argument via `SAVED_RDX` (the
  constant exists in the frame layout).
- **K3 ordering (§5).** If K3 lands before the K4 build, K3's own
  rule governs whether a faulting send buffer demand-loads or
  refuses, and the K4 build revisits its mapped-at-call-time rule
  then. Correctly flagged by the design; not resolvable on paper
  today.
- **§9 step 4 sequencing** lists the K3 build after the K4 gate.
  Lane order between the K3 build and the K4 build is Pax's
  scheduling call, not a design property; it does not block this
  approval either way.
- **Blocking receive** stays a separate, future designed step
  (wakeup wiring + death cases re-proved), exactly as §4 scopes
  it. Not required for the acceptance pair.

## Proof standard (unchanged)

Paper approval only. The K4 build merges solely on the §7 gate
pack run through OpenCode 1's Mac/QEMU gate, boot log read by Pax.
Nothing in this review is a compile, boot, or merge claim.
