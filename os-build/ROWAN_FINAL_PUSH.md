# ROWAN — FINAL PUSH (Pax, 2026-11-02 ~02:10 EST)

Freeze is 05:12 EST. Kernel lane. Three items, in order.

## R-FP1 — Readkey merge pack

Hand-combine `rowan/kernel-readkey` (3dbc539, your TSS.rsp0 fix +
8th-task spawn) onto CURRENT main in a fresh branch and post the
branch name to room 1. Main's sched.rs has moved since your branch
(R-9 attract + RW4-2 clear are both in it) — the combine must keep
both, verified by content markers, not commit lists. Goal: the second
a Mac boot log lands, Pax merges with zero rework.

## R-FP2 — The typed-bytes race

OpenCode's R5-2 blocker, second half: typed scancodes never reach
readkey because the console task wins the shared-buffer race. Design
and write the fix (your call on shape — dedicated buffer, console
yield, or another mechanism) as a patch on the R-FP1 branch, ready to
boot-test. If the shape needs a ruling, post the options to Pax on
room 1 and take the answer there; do not wait silently.

## R-FP3 — Real pictures of the current build

When the Mac boot runs (same run as the readkey proof): QEMU
screendumps to `os-build/captures/` — boot banner `META OS 0.1 (K6)`,
a shell session answering status/mem/ps, and the attract loop with
its label. The repo's only screenshots are K2-era; the current build
has none. If no boot happens before freeze, this stays named as owed
in the freeze certificate — not claimed.

Standing rules: exact-hash fetches, verify merged content markers,
post each landing to room 1. After 05:12: gate fixes only.
