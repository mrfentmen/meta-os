# KERNEL READING — Bond, wave 2, 2026-11-02 (READ-ONLY)

No file under `kernel/src` was edited. HEAD `78862a5`.

## 73. `mem.rs` — the heap, ten lines

1. `HEAP_BUF` is a static 512 KiB byte array (`mem.rs:26`).
2. `HEAP` is `Option<Heap>` behind a `static mut` (`mem.rs:35`).
3. The allocator is a linked-list heap over that buffer.
4. It is installed as `#[global_allocator]` (`mem.rs:85`), so `Box`/`Vec` work.
5. Frames come from a bitmap `FrameAllocator` built from the boot memory map (`mem.rs:184-188`).
6. The mapper is rooted at the live CR3 and owns that allocator.
7. `mem_init` prints covered/free frame counts.
8. It allocates a probe frame and maps it (`mem.rs:196`).
9. It then proves `Box+Vec` and a 10k allocation stress.
10. It prints `mem summary: K4 up`; interrupts never allocate, and K4 is single-CPU.

## 74. Syscall numbers actually used

`kernel/src/user.rs:92-134`:

| Number | Call | Behaviour |
|---|---|---|
| 0 | exit | prints code, `exit_task()` |
| 1 | write | one page max, range validated, utf-8 or `[non-utf8 N bytes]` |
| 2 | sleep | `sleep_task(ticks)` |
| 3 | getpid | current task id |
| 4 | yield | `yield_task()` |
| 5 | read_key | raw scancode 0-255, or `u64::MAX` when empty |

Any other number prints `user bad syscall N refused` and returns `u64::MAX`.
`syscalls.rs` still holds an older draft table and is **not wired**
(`KERNEL_STATUS.md`).

## 75. Who touched `syscalls.rs`

`git log -- kernel/src/syscalls.rs` returns one commit:

```
4bf2367 Pax Merge Rowan K6 syscalls draft ... UNWIRED ...
```

So the file's content is Rowan's draft, but the commit that landed it is a
Pax merge. "Untouched by anyone but Rowan" is true of authorship, false of
commit history. It was not modified in this lane.

## 76. K-items marked done in `KERNEL_BUILDOUT_SPEC.md`

**None.** K1-K7 are written as build-out items; the spec marks no item
"done". The only staged one is K2 (readkey): `kernel/build.rs` contains
the readkey binary, but `kernel/src/main.rs` never starts it (grep count 0).
The gate log exists, the kernel does not run it.

## 77. Boot log per done K-item

| Build-out item | State | Boot log |
|---|---|---|
| K1 graphics wired | framebuffer.rs unwired | NONE |
| K2 readkey finished | built, not started in main.rs | `os-build/logs/readkey-gate-419c209-boot.txt` shows `readkey: enter seen, done got=9`, `user exit code 0`, `tasks 8 ticks 796`, no panic. Gate proof exists; not wired. |
| K3 demand paging / COW / swap | not built | NONE |
| K4 IPC | not built | NONE |
| K5 storage + filesystem | not built | NONE |
| K6 drivers beyond keyboard/text | not built | NONE |
| K7 long tail | not built | NONE |

## Cross-check with `KERNEL_STATUS.md`

KERNEL_STATUS claims K1-K6 **milestones** proven (boot, VGA console,
interrupts, paging, scheduling, syscalls). Those are the older milestone
names, not the build-out items above. Both use "K1"-"K6"; the collision is
a documentation trap, not a code bug.

## Evidence

- `os-build/logs/readkey-gate-419c209-boot.txt` (lines copied to
  `os-build/bond-evidence/logs/readkey-gate-lines.log`)
- `os-build/KERNEL_STATUS.md`
- `os-build/KERNEL_BUILDOUT_SPEC.md`
- `kernel/src/mem.rs`, `kernel/src/user.rs`, `kernel/src/syscalls.rs`
