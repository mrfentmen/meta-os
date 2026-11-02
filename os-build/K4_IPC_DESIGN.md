# K4 IPC — design note (design only, no kernel code)

**Assignment:** `os-build/ROWAN_NEXT_BLOCK.md` (Pax, 2026-11-02), item 5,
plus the buildout spec's K4 section (`os-build/KERNEL_BUILDOUT_SPEC.md`).
**Base checked:** origin/main `130f093` (2026-11-02; Pax Bond-crates
merge of Milo gate-1 GREEN bond/wave2, parent `6524eba` — crates/
only, zero kernel/ or os-build/ files, so no kernel or design impact;
the kernel files cited below were verified on that tree).
**Status:** design only. Nothing here is
compiled, built, or booted. Proof is the Mac + QEMU boot log through
OpenCode 1's gate, read by Pax — same standard as every kernel step
before it. `syscalls.rs` is FROZEN (F1) and is not touched by this
design; the two new numbers come from the reserved range via the
inline dispatch in `user.rs` (see §5).

## 1. Today: no channel exists

- There is no way for one task to send anything to another. The
  spec's K4 states it in one line: "No channel exists between tasks
  today. Design from what the kernel already has (task ids, the
  scheduler's queues): a minimal message pass — send to a task id,
  receive with a bound, a full box refuses rather than blocks
  forever. Buffy's talker/listener userspace pair is the acceptance
  test."
- The acceptance pair is a live gap, not a hypothetical: Pax's
  Buffy rulings on room 1 (2026-11-02) record R11-273, the
  talker/listener gap, as STANDING until Rowan ships IPC. Buffy
  writes the talker/listener programs; Rowan's deliverable is the
  kernel side plus the exact calling convention written down for
  her (assignment item 6). This note is that convention, before
  any code.
- What the kernel already has, all on main, that this design
  builds on:
  - `kernel/src/user.rs`, `syscall_handler` (vector 128): reads the
    saved registers, dispatches 0–5 inline (exit, write, sleep,
    getpid, yield, read_key), and refuses anything else with a
    `user bad syscall … refused` log and return `u64::MAX`.
  - `kernel/src/user.rs`, `user_write`: validates the whole caller
    buffer with `is_mapped_range` and caps one call at 4096 bytes;
    an unmapped buffer is refused, never faulted into existence.
  - `kernel/src/sched.rs`: cooperative scheduler over a static
    slot table (`MAX_TASKS = 8`), parallel arrays (`CTXS`, `IDS`,
    `SLEEPS`), `CUR` for the running task, `find_row(id)` for the
    slot row, and `yield_task` / `sleep_task` / `exit_task` as the
    existing task-state transitions. `tasks.rs` supplies
    `Scheduler::block_current`, `unblock`, `exit_current`,
    `yield_now`, and the `Ready` / `Running` / `Blocked` /
    `Exited` states.
  - The non-blocking idiom, already proven by read_key (R-7):
    an empty source returns `u64::MAX`, and the caller polls, or
    sleeps/yields between polls. No caller ever blocks inside a
    getter waiting for data to appear.

## 2. What changes, in one sentence

Each task gets one small mailbox; a task sends a copied message to
another task's mailbox by id, and the recipient receives a copy out
of its own mailbox — both operations non-blocking, both refusing
with `u64::MAX` instead of waiting, and a dead peer's mailbox
being discarded on exit while already-delivered messages survive
as the recipient's property (§4).

## 3. The primitive, exactly

**Mailbox.** One per scheduler slot row, kernel-owned static
storage, no heap allocation, no page sharing:

- Capacity: exactly **one message** per recipient. This is the
  smallest box that satisfies the spec's sentence: a second send
  to an occupied box is refused, deterministically, which is
  itself a gate leg (§7). A multi-message queue is a named later
  step, not silently added here.
- Payload: at most **64 bytes**, length-carried. A message is
  `(sender_id, len, bytes[64])`, where `sender_id` is filled in
  by the kernel from `sched::current_id()` — never caller-supplied,
  so a message cannot forge its sender.
- Copy semantics: `send` copies the sender's buffer into the
  recipient's mailbox; `recv` copies the mailbox out into the
  receiver's buffer and empties the box. The sender mutating its
  buffer after a successful send does not change the queued
  message, and the receiver mutating its buffer after a receive
  does not affect anyone else. There is no shared page, no
  zero-copy, and no aliasing to reason about.

**Addressing.** Send addresses a task id, exactly as the spec
says — not a named channel, not a port number, not a capability.
Any live row in the scheduler table is addressable. A send to
oneself is allowed (loopback, and a useful first test). A message
sent to a task that never receives simply sits in its box until
that task exits, when it is discarded (§4); the gate pair are
both userspace, so kernel-task addressing is out of gate scope.

**Validation, in order, all before any copy or state change:**

1. Destination id is a live row (`find_row` succeeds and the
   slot is not `Exited`). A dead, never-spawned, or id-0
   destination is refused.
2. The caller buffer is fully mapped (`is_mapped_range`, the
   `user_write` rule) and the length is in range: send `1..=64`
   (zero-length sends are refused — an empty message carries
   nothing, and emptiness is the mailbox-empty signal); receive
   buffer capacity `>= 72` (64 payload bytes plus the 8-byte
   sender-id header, §6), so a message is never truncated.
3. For send: the destination box is empty. A full box is refused,
   the queued message untouched, the sender's buffer untouched.
4. For receive: the caller's own box is non-empty. An empty box
   returns `u64::MAX` and changes nothing.

A refusal changes no mailbox state and consumes nothing. Every
refusal is logged in the existing kernel style (see §7 for the
wording the gate log must show).

## 4. Blocking semantics, and what happens when a peer dies

**Blocking semantics: none, in step 1.** Both operations are
non-blocking, deliberately:

- `send` to a full box refuses rather than blocking forever —
  the spec's own words, and the reason no sender can deadlock
  behind a listener that never runs.
- `recv` on an empty box returns `u64::MAX` rather than
  blocking — the read_key idiom, extended to messages. A
  receiver that wants to wait polls, sleeping or yielding
  between polls with the existing syscalls 2 and 4.
- This is what keeps step 1 small: with no blocking, there is
  no blocked-receiver wakeup path for `send` to implement, no
  wait queue to maintain, and no wake-on-death path. A blocking
  receive (park the receiver in `Blocked`, wake it from `send`)
  is a real later step — it needs `block_current`/`unblock`
  wiring plus the death cases below re-proved — but it is not
  this step, and the talker/listener pair does not need it: one
  message at a time, polled, is enough for the pair to exchange
  a message and prove the primitive.

**Peer death:**

- **Recipient dies:** `exit_task` clears the exiting task's
  mailbox. A message still queued for it is discarded with it —
  it was never received, and there is no dead-letter box in
  step 1. Any later send to that id is refused at validation
  step 1 (the row is `Exited`).
- **Sender dies:** a message already copied into the
  recipient's mailbox survives the sender's exit. The mailbox
  copy is recipient-owned; delivery is complete at `send`
  return, not at `recv`. The receiver therefore gets the
  message with the dead sender's id attached, and must not
  assume the sender is still alive: a reply send to that id
  will be refused, and the poll pattern handles that like any
  other refusal.
- **Sender dies mid-exchange:** there is no mid-exchange
  window in step 1. `send` is a single copy under the syscall
  handler on the sender's own kernel stack, on a single CPU
  with a cooperative scheduler — it either returns having
  queued the copy, or refuses having queued nothing. No
  partial message can exist in a box, because a box holds
  either one complete message or nothing.
- **Third task:** unaffected by construction. Mailboxes are
  per-row; a send touches only the destination row, a receive
  touches only the caller's row, and no other task's state,
  sleep deadline, or queue position changes. The gate proves
  this (§7), it is not asserted here.

## 5. Fences respected, and the syscall numbers

- `syscalls.rs`: untouched (F1 FROZEN). The authoritative
  dispatch is the inline `match` in `user.rs::syscall_handler`,
  and this design extends exactly that match — the same place
  0–5 already live, the same saved-register convention
  (`rax` = number, `rdi` = first argument, `rsi` = second,
  `rdx` = third, per the frame layout `user.rs` documents).
- Numbers: **6 = ipc_send, 7 = ipc_recv**, the first two of the
  reserved range 6–15. K3 step 1 consumed none of the reserved
  range (its promised region is loader-registered, not
  userspace-requested), so 6 and 7 are the first free numbers,
  and this design argues for them because userspace must invoke
  the primitive from ring 3 and there is no other entry path.
  If Pax's review assigns different numbers, the build step
  uses Pax's numbers and this note is corrected — the numbers
  here are the design's proposal, not a unilateral claim.
- K3 demand paging, K5 storage/filesystem, copy-on-write, and
  shared memory are all out of scope. One interaction is named
  so the build step does not trip on it: `send` validates the
  buffer as mapped *at call time* and refuses an unmapped
  buffer, the `user_write` rule. K3's build has not landed, so
  there is no demand path to consult yet; if K3 lands first,
  its build must say whether a faulting send buffer becomes a
  demand fault or stays a refusal, and this design's rule is
  revisited then — not assumed now.

## 6. Calling convention (for Buffy's talker/listener)

All values are `u64`. Return `u64::MAX` always means refused
or empty — the same sentinel `user_write` and `read_key`
already use. Anything else is a success count.

**`ipc_send` — syscall 6:**

- `rdi` = destination task id (as returned by `getpid`, syscall 3).
- `rsi` = sender buffer address. `rdx` = message length, `1..=64`.
- Returns `0` on success (message queued in the destination
  box). Returns `u64::MAX` on any refusal: bad or dead
  destination, unmapped buffer, length out of range, or a full
  box. The kernel log names the reason; the return code does
  not distinguish them, matching the existing refusal style.
- Sending to oneself queues in one's own box and is received
  by one's own later `ipc_recv`.

**`ipc_recv` — syscall 7:**

- `rdi` = receiver buffer address. `rsi` = buffer capacity,
  which must be `>= 72`. A smaller buffer is refused without
  consuming the message: truncation would silently lose bytes,
  and a caller that always allocates the documented 72-byte
  buffer never hits this case, so a stuck message cannot arise
  from a conforming caller.
- Returns the number of bytes copied on success, and the box
  is emptied. The copied bytes are laid out as: bytes
  `[0..8)` = sender task id, little-endian `u64` (kernel-filled,
  never caller-supplied), followed by the payload bytes. So a
  successful return is `8 + payload_len`, i.e. `9..=72`, and
  the caller reads the sender from the first 8 bytes and the
  message after them. One call, no extra state, no second
  syscall for the sender id. Returns `u64::MAX` when the box
  is empty or the call is refused (unmapped buffer, capacity
  too small).
- Polling pattern (the read_key pattern, reused): call
  `ipc_recv`; on `u64::MAX`, `sleep` or `yield`, then retry.
  Never spin without yielding — a spinning receiver starves
  the sender on this cooperative scheduler.

**Talker/listener sketch (Buffy's programs, not Rowan's):**
talker `getpid`s the listener's id (the pair's ids are fixed
by spawn order in the gate build — see Q-I1), sends one
message, and exits; listener polls `ipc_recv` until it
receives, prints the message, and exits. Neither program needs
any kernel knowledge beyond this section.

## 7. Gate pack for OpenCode 1 (the boot log must show all of this)

One boot, no panic, console task alive throughout, a third
task (e.g. sleeper or hello) running to its normal exit
unaffected:

1. **Exchange leg:** talker sends; the log shows a send line
   (sender id, destination id, length, in the existing
   `user …` log style); listener receives; the log shows the
   received message and the sender id; both exit normally.
2. **Full-box refusal leg, same boot:** talker sends twice
   before the listener receives; the second send is refused
   (log names the full box, return `u64::MAX`), the first
   message is untouched and is then received intact.
3. **Empty-receive leg, same boot:** a receive on an empty box
   returns `u64::MAX` and changes nothing; the caller polls
   and later receives normally.
4. **Dead-peer leg, same boot:** a send to an exited task's id
   is refused (log names the dead destination); a message
   sent before its sender exits is still received after the
   sender's exit, with the dead sender's id attached.
5. **Negative leg:** a send with an unmapped buffer and a
   receive into an undersized buffer are both refused, with
   no mailbox state changed and no task killed.

Gate failure modes that must NOT be papered over: an exchange
leg that passes only because the pair shared memory or a
global instead of the mailbox; a refusal leg missing its log
line; a boot where the third task dies or the console stops;
any panic. A log that shows only successful exits, without
the send/receive lines, proves nothing.

## 8. Open questions for the build step (not assumed here)

- **Q-I1 — slot budget.** `sched.rs` records the table as
  "now full at 8/8 with readkey". The gate pair needs two
  userspace slots. The build step must say whether the gate
  build swaps demo programs out or grows the table — this
  design assumes neither, and the pair cannot be added to a
  full table by wishing.
- **Q-I2 — where the mailbox state lives.** The natural home,
  following the existing parallel-array pattern, is `sched.rs`
  alongside `SLEEPS` (one box per row, accessed via
  `sched::ipc_send` / `sched::ipc_recv` called from the
  `user.rs` dispatch, mirroring `sleep_task` / `yield_task` /
  `exit_task`). A separate `ipc.rs` module is also defensible.
  The build step names the home and the single-CPU soundness
  note for it, in the style of the existing OS-086 ledger
  comment; this design does not pre-commit the file.
- **Q-I3 — slot reuse.** `sched.rs` runs with no reap in K5
  (slots fill in spawn order and stay), and `tasks.rs` has a
  `reap` that this kernel does not use. This design clears a
  mailbox on `exit_task`, so a recycled id could never inherit
  a queued message — but if reap ever lands, the build step
  for it must re-prove that exit-clearing still holds on the
  reap path, not assume it.

## 9. Build order after this design

1. This note (this branch) — Pax review, including the 6/7
   number proposal and the Q-I1 slot answer.
2. Build step: mailbox state (Q-I2), dispatch entries 6/7 in
   `user.rs` only, exit-path discard, one gate pair run by
   Buffy's programs against the §6 convention.
3. Gate pack (§7) through OpenCode 1's Mac gate; Pax merges
   only on that gate log.
4. Then, in order: K3 build (if not already landed), blocking
   receive as its own designed step if the pair's users need
   it, and K5 stays design-only until K3 lands, per the
   assignment.
