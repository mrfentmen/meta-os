# Bootloader spike executed (MORE_TASKS #5) — tip fdd472e0, scratch branch spike/bootloader-0.11

Spike: KERNEL_FACE_PART2 (0a82f58c): Route 1 = 0.11.x first
(0.11.17 cited), 0.10.x fallback. Pinned one version at a time,
plain `cargo build --target x86_64-unknown-none` in kernel/
(with userspace bins prebuilt per gate.sh). No source edits
beyond the version pin — the API rewrites are Rowan's lane.

## Attempt 1: bootloader 0.11.17 — BUILD FAILS (deps need std)

`error[E0463]: can't find crate for std` (x6+ shown, 5829 total
errors), `error: could not compile serde_core (lib)`. The 0.11
dependency tree pulls serde/host-side derives that cannot build
for the no_std kernel target at all. No kernel object produced.
Full log: /tmp/spike-build.log (kept on the Mac; tail committed
in the report).

## Attempt 2 (fallback): bootloader 0.10.9 — BUILD FAILS (0.9 API gone)

Deps compile; the kernel source (written for 0.9) does not:
`error[E0433]: cannot find bootinfo in bootloader` (x2),
`error[E0408]: variable KernelStack/PageTable/Bootloader/
BootInfo/FrameZero/InUse is not bound in all patterns`,
15 errors total, `could not compile metaos-kernel (bin)`.
Full log: /tmp/spike-build-010.log.

## Outcome

No boot, no screendump: BOTH routes stop at build time, before
any image exists. Making either go needs the kernel source
rewrite to the new bootloader API (entry macro, BootInfo
path, framebuffer handover) — Rowan's lane, not this one.
Route decision input for Pax: 0.11.x is a dead end without a
std-shim strategy for its dep tree; 0.10.x at least resolves
deps, and the remaining work is source-only.
