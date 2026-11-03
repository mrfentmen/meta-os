# Userspace programs — spec first, one program per proof

**Build pipeline (fixed 2026-11-02):** programs are built with
`os-build/userspace/build.sh`, which gives each one its own link base from
`bases.txt` and verifies the ELF headers. Before this, every bin linked at the
same address and the kernel refused 3 of 4 with `address in use`. Proof:
`os-build/logs/K6-bases-fixed.txt` and `os-build/userspace/BASES.md`.

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
| `quitter` | exit status is reported truthfully | `quitter: exiting 7`, `user exit code 7` | **BUILT at 0x6400…, base verified**; needs one line in `BINS` to be wired |
| `readkey` | syscall 5 returns real scancodes | `readkey: polling syscall 5`, `readkey got <n>`, `readkey: empty` | **WRITTEN, COMPILES**; a diagnostic probe, not for `BINS` |
| `writer` | the one-page write cap is enforced | `writer: alive`, `writer: oversize returned 0`, `writer: cap returned 19` | **WRITTEN, COMPILES**; probe, not for `BINS` |
| `badcall` | reserved numbers 6-15 refuse, not just 99 | `user bad syscall 6 refused` / `15` / `99`, then `badcall: 6 returned 18446744073709551615` and `badcall: survived all three` | **WRITTEN, COMPILES**; wiring proposal |
| `hog` | allocation is bounded and contained | `hog: allocating`, then the task killed by the fault; the shell must still answer `status` afterwards | **WRITTEN, COMPILES**; fault-containment drill, not an allocator test — no allocation syscall exists (wiring proposal: `os-build/userspace/WIRING_PROPOSAL_R12.md`) |
| `talker` + `listener` | two tasks can exchange a message | `talker: sent <n>`, `listener: got <n>` | **BLOCKED — no IPC exists** |
| `abiprobe` | the six-call contract itself | `abiprobe: checks 9 failures 0`, `abiprobe: ABI OK` | **WRITTEN, BUILT** at 0x6818…, base verified; diagnostic, needs `BINS` + a fifth stack slot |
| `selfinfo` | syscall 3 identity survives sleep | `selfinfo: pid <n>`, `selfinfo: identity held` | **WRITTEN, BUILT** at 0x6819…, base verified; diagnostic |
| `writechain` | repeated and chunked writes | `writechain: failures 0`, `writechain: OK` | **WRITTEN, BUILT** at 0x681a…, base verified; diagnostic |
| `yielder` | a yield returns to the same task | `yielder: yields 8 failures 0`, `yielder: identity stable` | **WRITTEN, BUILT** at 0x681b…, base verified; diagnostic |

## The corpus is now fully buildable (2026-11-02)

All 36 bins in `user/src/bin/` are in `bases.txt` and build. `verify_bases.py` reads the real
ELF headers and reports every image disjoint, at its manifest base, entry inside its own
image; the measured table is `os-build/USERSPACE_BUILD_STATUS.md`. The 32 that were previously
unlisted had no slot at all, so this is the first time the whole corpus has been checked rather
than the four programs the kernel happens to embed.

`lib.rs` gained the pieces a real program needs: `sys_write_all` (splits at the kernel's
4096-byte cap instead of being refused), `print_hex`, and `print_i64` (including `i64::MIN`).
`abiprobe` is the program that checks those claims from ring 3 rather than in prose.

## Why two of the six are blocked, and why that is the deliverable

`hog` cannot test allocation, because there is nothing to allocate with. The kernel's userspace
ABI is six calls (0 exit, 1 write, 2 sleep, 3 pid, 4 yield, 5 read_key) and 6-15 are reserved by
the F1 ruling; there is no `mmap`, no `brk`, no `alloc`. What is written is the refusal path that
does exist: `hog` touches pages past its image, the first unmapped page faults, and the kernel
kills only that task. That is containment by fault kill, and the program says so in its own
source. A real allocation drill still needs a memory syscall: **Pax assigns the number, Rowan
implements it, then `hog` changes.**

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
