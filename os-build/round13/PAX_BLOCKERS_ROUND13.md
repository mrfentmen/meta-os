# Round 13 — blockers

Grouped by who can clear them. No softening: if nothing in a group is blocked, the group is absent.

## Pax

- MERGED: `buffy/round13` landed as `e2b2c587` (tip `368c617d`). Nothing left to merge.
- Relay `os-build/round13/userspace/PROPOSALS.md` to Rowan + OpenCode on room 1; this lane has no bus access.
- Decide whether Section S's `cargo check` is a Mac-gate job or a host fix.

## Rowan + OpenCode (Mac gate)

- `cargo check` and boot for the 25 userspace programs; wire them into the boot manifest; return the boot log.
- Six syscalls proposed in `PROPOSALS.md` (argv, spawn, wait, kill, mmap, munmap, ps). `kernel/src/syscalls.rs` is FROZEN and was not touched.

## Milo

- Audit the 4 OPSEC failures in `os-build/round13/aegis/SECTION_J.md`, in particular 1,422 commits authored from a consumer mail domain.
- The ledger has no dedupe key and no closure field; that is a gate question, not a code one.

## Boss

- R13-152: one bearer-shaped token in history, no longer in the tree. Counts cannot close it; review only.
- The direct-`api.osv.dev` route exception for Sections E and F needs a written yes or a BLOCKED reading.

## Not blocked — simply absent

- There is no cadence loop and no federation module. No agent can clear that by waiting; it is a build decision.

Round 13 task: R13-500.
