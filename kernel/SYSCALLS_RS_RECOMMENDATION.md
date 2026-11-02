# Recommendation: delete `kernel/src/syscalls.rs` (for the boss's 2026-11-02 ruling)

From Rowan, 2026-11-01 ~20:40 EST, Round 4 task RW4-5.
Status: WRITTEN (a recommendation, not a ruling). Per the F1
freeze, `syscalls.rs` itself is untouched tonight.

## The recommendation

Delete `kernel/src/syscalls.rs` when the boss rules on
2026-11-02. Do not wire it in. If a separate dispatch module is
ever wanted again, extract it from the live dispatch in
`kernel/src/user.rs` — do not resurrect this file's table.

## Why

1. **It is dead code.** `main.rs` does not declare the module.
   It is 484 of the 1,060 dead lines Pax counted in the tree
   tonight (the other 576 are the framebuffer). Dead code that
   looks load-bearing is worse than no code.

2. **Its numbers conflict with the frozen F1 table.** This is
   the sharp reason. Side by side:

   - `syscalls.rs`: 0 exit, 1 write_serial, 2 write_console,
     3 read_key, 4 ticks, 5 yield.
   - F1 (live, in `user.rs` and now in `KERNEL_SPEC.md`):
     0 exit, 1 write, 2 sleep, 3 pid, 4 yield, 5 read_key.

   Every number from 2 on means a different thing. Userspace
   built against the `syscalls.rs` numbers would not fail
   loudly — it would silently do the wrong thing: ask for a
   key and get its own task id back (3), ask to yield and read
   a key instead (5). Two live-looking tables for one syscall
   vector is a trap, and traps get deleted, not documented
   around.

3. **The live path already covers its ground.** `user.rs`
   validates the write buffer (mapped range, one-page cap),
   and dispatches exit / write / sleep / pid / yield today.
   The one F1 call it lacks, `read_key` (5), belongs in
   `user.rs` under RW4-1 — wiring `syscalls.rs` to get it
   would import a second, conflicting dispatcher to serve
   one call.

4. **Wiring it means replacing proven code with unproven
   code.** The `user.rs` dispatch is the one the merged tree
   boots with. `syscalls.rs` was drafted unwired, against
   draft numbers, and has never run. "Wire it deliberately"
   would be a rewrite wearing a wiring's clothes.

5. **Nothing of value is lost by deleting.** The full text,
   including its design notes (kernel-owned copied buffer,
   fault-final outcomes, the `NO_KEY` empty-ring sentinel),
   stays in git history. The one idea worth keeping — the
   `u64::MAX` sentinel for an empty key ring — can be adopted
   in `user.rs` when `read_key` lands there; it does not need
   the file to survive.

## What deletion must not touch

- `kernel/src/user.rs` — the live dispatch, unchanged.
- The F1 table in `KERNEL_SPEC.md` — it stands either way.
- Any userspace program: none is built against the
  `syscalls.rs` numbers (they were draft-only, per Q12).

## Counts for this report

Files touched by this recommendation: none in `kernel/src`.
Dead lines in `kernel/src` tonight: unchanged at 1,060
(576 framebuffer + 484 syscalls) until the boss rules; a
deletion on 2026-11-02 would take the dead count to 576,
all of it the parked framebuffer.
