# Userspace programs — spec first, one program per proof

Lane rule: a program's expected boot-log lines are written **before** the program, and the
program is done when the log matches the spec. Sources live in
`os-build/userspace/user/src/bin/`; the kernel embeds them through `kernel/build.rs`, whose
`BINS` list is in Rowan's lane. So a program here is *written and compilable* but **not
wired** until that list changes — the wiring is a proposal, not an edit.

## Status

| Program | Claim it extends | Expected boot-log lines | Status |
|---|---|---|---|
| `hello` | ring 3 runs at all | `HELLO FROM USERSPACE`, `user exit code 0` | PROVEN (`K6-boot.txt`) |
| `sleeper` | sleep/wake from userspace | `sleeper: before sleep`, `sleeper: pid <n>`, `sleeper: after sleep` | PROVEN (`K6-boot.txt`) |
| `crasher` | fault isolation | `crasher: about to read zero`, `INT user page-fault addr 0x0 err 0x4: task killed` | PROVEN (`K6-boot.txt`) |
| `quitter` | exit status is reported truthfully | `quitter: exiting 7`, `user exit code 7` | **WRITTEN, COMPILES**; needs one line in `BINS` to be wired |
| `readkey` | syscall 5 returns real scancodes | `readkey: polling syscall 5`, `readkey got <n>`, `readkey: empty` | **WRITTEN, COMPILES**; a diagnostic probe, not for `BINS` |
| `hog` | allocation is bounded and contained | `hog: allocating`, then either a refusal line or the task killed; the shell must still answer `status` afterwards | **BLOCKED — no allocation syscall exists** |
| `talker` + `listener` | two tasks can exchange a message | `talker: sent <n>`, `listener: got <n>` | **BLOCKED — no IPC exists** |

## Why two of the six are blocked, and why that is the deliverable

`hog` cannot be written honestly. The kernel's userspace ABI is six calls (0 exit, 1 write,
2 sleep, 3 pid, 4 yield, 5 read_key) and 6-15 are reserved by the F1 ruling. There is no
`mmap`, no `brk`, no `alloc` — a userspace program has no way to ask for memory at all. Writing
`hog` against a syscall that does not exist would be exactly the mock the spec forbids, so the
finding goes to Rowan instead: **`hog` needs a memory syscall, and that is a Pax number ruling
before it is code.**

`talker`/`listener` are blocked for the same class of reason but deeper: the kernel has no IPC
of any kind (no queue, no shared page, no signal). `KERNEL_BUILDOUT_SPEC.md` section K4 designs
it; nothing implements it. Two tasks can currently only communicate through the console (both
write), which is not a channel and cannot be made to look like one.

## `quitter` — the line format, then the program

Specified first: the kernel's exit arm prints `user exit code {}` (`kernel/src/user.rs`,
dispatch arm 0), then `ps` reports the slot as `Exited`. So `quitter` must produce exactly:

```
quitter: exiting 7
user exit code 7
```

The program (`quitter.rs`) writes its line and calls `sys_exit(7)`. It is deliberately not 1:
1 is the code a defaulted or crashed exit tends to produce, so a deliberate 7 cannot be
mistaken for a loader failure.

Wiring proposal to Rowan: add `"quitter"` to `const BINS` in `kernel/build.rs`, rebuild the
userspace crate, then the kernel. No kernel source change beyond that one list entry.

## What "compiles" means here

`cargo build --target x86_64-unknown-none --bins` in `os-build/userspace/user` succeeds with
`quitter` present. That is a userspace-crate compile, **not** a kernel boot, and it is not a
claim that the kernel embedded or ran it.

That build was red when this file was first written: the `readkey` bin imported
`sys_read_key`, which `lib.rs` never defined, and carried a string literal split across a
newline. Both are fixed (the wrapper returns `syscall(5, 0, 0, 0)`; the literal is `b"\n"`),
and the crate now builds all its bins. Recording it because the first version of this page
claimed a green build it had not run — which is the exact failure mode this repo keeps having.
