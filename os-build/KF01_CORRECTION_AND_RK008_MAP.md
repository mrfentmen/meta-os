# KF-01 correction + RK-008 API map — Pax, 2026-11-02

Status labels: docs.rs facts VERIFIED (pages read 2026-11-02). Our-code
usage CODE-INSPECTED (verify-clone; kernel/src unchanged on main since
c7aeb162). The wrong-crate diagnosis is an INFERENCE — high confidence,
from the error class plus the crate split below. No boot is claimed.

## The finding

The recorded 0.11.17 spike attempt never tested the 0.11 kernel API.
Evidence: `os-build/logs/SPIKE_BOOTLOADER_RESULT.md` on branch
`spike/bootloader-0.11` @db0b0020 (parent = opencode/round7 tip):

- Attempt 1, bootloader 0.11.17: build fails with 5,829 errors,
  `error[E0463]: can't find crate for std`, `could not compile
  serde_core`. The pin put the `bootloader` crate itself into the
  no_std kernel manifest.
- Attempt 2, bootloader 0.10.9: deps compile; the 0.9-era kernel
  source fails (15 errors: no `bootinfo` module, memory-kind variants
  unbound). Source-only failure.

docs.rs, read today:

- `bootloader` 0.11.17 is the HOST-side image builder: `BiosBoot`,
  `UefiBoot`, `DiskImageBuilder` ("Create disk images"). It is built
  for the host, so it pulls std/serde — exactly the attempt-1 errors.
- `bootloader_api` 0.11.17 is the KERNEL-side interface: "Provides the
  interface to make kernels compatible with the bootloader crate."
  It exports `BootInfo`, `BootloaderConfig`, and the `entry_point`
  macro. Kernels depend on `bootloader_api`, never on `bootloader`.

Diagnosis: attempt 1 pinned the wrong crate. 0.11 is not a dead end;
the attempt was malformed. RK-006's pin on `rowan/bootloader-spike`
@1f006090 repeats the same pin (`bootloader = { version = "0.11" }`
in kernel/Cargo.toml) and will hit the same wall on the Mac.

## Budget ruling (Pax, amends the 2026-11-02 KF-01 budget post)

The malformed attempt does not consume budget. The 2 fresh attempts
stand, redefined:

1. Attempt 1 = corrected 0.11.17: `bootloader_api` pin + the RK-008
   source rewrite below + host-side image build. Verbatim build and
   boot logs or it does not count.
2. Attempt 2 = Rowan's pick if attempt 1 fails with logs: another
   0.11.x patch, or the 0.10.9 route (deps proven to compile in the
   spike; the rewrite there is the same shape).

If both fail with logs: restore the 0.9.35 pin, re-run gate.sh GREEN
7/7, file the evidence, stop. The route call after that is Pax's.

## RK-008 API map (0.9.35 → bootloader_api 0.11.17), Rowan's rewrite

1. **Manifest.** kernel/Cargo.toml: drop `bootloader = "0.9"` and the
   `map_physical_memory` feature; add `bootloader_api = "0.11"`
   (resolves 0.11.17). Physical-memory mapping is config now, not a
   cargo feature (this supersedes RK-006's forced note).
2. **Entry.** main.rs: `bootloader::entry_point!(kernel_main)` →
   `bootloader_api::entry_point!(kernel_main, config =
   &BOOTLOADER_CONFIG)` with a `BootloaderConfig` static whose
   mappings request the physical-memory offset (config module:
   `bootloader_api::config`). Signature changes:
   `fn kernel_main(boot_info: &'static BootInfo)` →
   `&'static mut BootInfo` (0.11 entry signature, docs.rs).
3. **Physical offset.** `boot_info.physical_memory_offset` changes
   from plain `u64` (0.9) to `Optional<u64>` (0.11), present only
   when the config maps physical memory. main.rs (the VGA pointer
   arithmetic at the current line ~131) and mem.rs must unwrap it.
4. **Memory map.** `boot_info.memory_map` → `boot_info.memory_regions`.
   mem.rs `kind_of`: 0.9 `bootloader::bootinfo::MemoryRegionType`
   (Kernel, KernelStack, PageTable, Bootloader, BootInfo, FrameZero,
   InUse, …) is replaced by `bootloader_api::info::MemoryRegionKind`
   with exactly four variants — `Usable`, `Bootloader`,
   `UnknownUefi(u32)`, `UnknownBios(u32)` — and it is
   `#[non_exhaustive]` (wildcard arm required). Consequence: the map
   no longer distinguishes kernel/stack/page-table regions; anything
   not Usable or Bootloader arrives as Unknown* with the raw firmware
   tag and must be treated as not-usable. BootInfo separately carries
   `kernel_addr`, `kernel_len`, `kernel_stack_bottom`,
   `kernel_stack_len` if the kernel needs its own extents.
5. **Framebuffer (KF-03).** `boot_info.framebuffer` is
   `Optional<FrameBuffer>`. `FrameBuffer::buffer_mut()` /
   `into_buffer()` yield the pixel bytes (`&'static mut [u8]` via
   `into_buffer`); `info()` yields the geometry and pixel format.
   That is exactly the boundary `kernel/src/framebuffer.rs` was
   written against (it imports no bootloader type; the wiring commit
   is the thin adapter into its `FramebufferInfo`).
6. **Image build (Mac lane / gate).** The 0.9 bootimage flow does not
   exist in 0.11. Images are created host-side with the `bootloader`
   crate (`UefiBoot` or `BiosBoot`, `create_disk_image`). gate.sh's
   image step changes accordingly; QEMU flags follow the choice
   (OVMF for UEFI). This is tooling, not kernel source.
7. **Fences.** kernel/src/syscalls.rs stays FROZEN. Only Rowan writes
   kernel/src. The rewrite lands on `rowan/bootloader-spike` as a new
   commit superseding RK-006's manifest.

## What is still owed after this lands

Rowan: corrected pin + rewrite on the spike branch, Milo gate-1.
Mac lane: build, boot, screendump set, verbatim logs committed.
Pax: read the logs, then KF-02 gate call. Until then KF-01 stays
BLOCKED — on a corrected, buildable attempt instead of a malformed one.
