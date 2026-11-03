# REAL-OS 4-HOUR CRANK — plan only, no implementation yet

Owner: OpenCode 1. Basis: honest audit of 2026-11-02 (kernel ~6,000 lines
across 13 files; 6 syscalls; ELF loader real; scheduler cooperative-only;
no FS, no disk/net/USB drivers; agents host-side only).
Branch: opencode/500. Status: PLAN COMMITTED — work has NOT begun.

## Goal (what 4 hours buys)
A real interactive multi-program system with a guest-driven agent loop —
terminal class in QEMU, every claim proven by a committed boot log. NOT a
desktop OS (see non-goals).

## Targets, in order
1. **Exec from shell (~1h).** `run <name>` in the shell loads the matching
   embedded ELF through the existing loader (`kernel/src/user.rs:277`).
   Acceptance: boot, type `run sleeper`, new task appears in `ps` with its
   own ticks; committed serial shows the spawn + output.
2. **Guest↔host agent bridge (~1.5h).** Serial `EVENT:` line protocol:
   guest program emits event → host daemon reads serial → runs crew
   assessment → sends command back via monitor sendkey. First genuine
   guest-DRIVEN loop (today it is host-scripted). Acceptance: unscripted
   guest event produces a crew assessment + a guest-visible response,
   all three legs committed.
3. **Preemptive timer switch (~45m + soak).** Wire the existing quantum
   fields to the timer IRQ (`kernel/src/sched.rs` documents the gap).
   Acceptance: two CPU-bound tasks interleave ticks with no yields;
   30-min soak panics 0.
4. **RAMFS + open/read/write (~45m).** In-memory files so programs keep
   state within a boot. Acceptance: write from one program, read back
   from another after reboot-of-tasks (not of machine).
5. **Gate + soak + commit (~30m).** Full gate GREEN + ≥30-min soak on the
   new tree; 283-proof index extended; STATUS updated.

## Stretch (only if 1–5 land early)
- Password gate at boot (hashed check, ~30m once RAMFS exists).

## Explicitly OUT of scope for the 4 hours
Desktop/GUI, disk drivers, TCP/IP, USB, demand paging (K3 FAILED, Rowan's),
IPC pair (K4 UNIMPLEMENTED), real-hardware boot. Anyone promising these in
4 hours is repeating the theater this plan replaces.

## Fences (unchanged)
kernel/src/syscalls.rs FROZEN. No face/web work. Simulated loopback
dispatch only. No padded counts — every number from a named command on a
named tree. Commit per target; Pax merges.
