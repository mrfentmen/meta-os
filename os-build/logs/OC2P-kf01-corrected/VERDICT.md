# OC2P KF-01 corrected attempt — VERDICT (support lane, 2026-11-02/03 UTC)

- Commit built: `717e7ffb` (RK-008: bootloader_api 0.11.17 pin + source rewrite)
  in scratch worktree `/tmp/oc2b-kf01-correct` (detached, `--detach`).
  Tree left CLEAN (`git status --short` empty). No kernel source edited anywhere.
  No push, no commit, no other worktree touched.
- rustc: stable `1.99.1` (host default) / nightly `1.101.0-nightly (f9ceb4a4d 2026-10-31)`
  (builds used nightly on PATH + `RUSTC_BOOTSTRAP=1`, gate.sh flags
  `-C relocation-model=static -C code-model=large -C link-arg=-no-pie`).

## OC2P-001 BUILD — PASS (kernel object produced)

- Userspace prebuild (gate.sh per-pair link scripts): hello/sleeper/crasher/readkey
  all `cargo build --target x86_64-unknown-none` exit 0 (nightly flags). ELFs verified.
- `cargo bootimage` exact result: KERNEL COMPILED (0 errors, 24 warnings —
  matches the commit message's "0 errors, 24 pre-existing warnings"), then the
  image step failed as expected on 0.11 with:
  `Error: An error occurred while trying to build the bootloader: Bootloader dependency not found`
  `You need to add a dependency on a crate named 'bootloader' in your Cargo.toml.`
  (exit 1; RK-008 eliminated the 0.9 flow — recorded, not worked around).
- Branch-supported flow: `cargo check` exit 0, `cargo build --target x86_64-unknown-none`
  exit 0. Kernel ELF `kernel/target/x86_64-unknown-none/debug/metaos-kernel`:
  14720088 bytes, ELF 64-bit LSB x86-64 statically linked, with 133-byte
  `.bootloader-config` section PRESENT (physical-memory mapping flag set).
- Verbatim: `/tmp/oc2p-kf01/OC2P-kf01-corrected-build.txt`
  (copy at `/tmp/OC2P-kf01-corrected-build.txt`).

## OC2P-002 IMAGE — PASS (no API mismatch; first shape worked)

- RK-008 step 6 verified against bootloader 0.11.17 source (local cargo registry):
  `BiosBoot::new(&kernel_path)` + `create_disk_image(&out)` — matches the map.
  No API error; no alternative shape needed.
- One build-environment note (not an API/semantics change): bootloader 0.11.17's
  build.rs shells out to nightly-only `cargo -Zbuild-std`, so the host tool was
  built with nightly cargo (same family gate.sh mandates) after
  `rustup target add x86_64-unknown-uefi`. Tool source: `/tmp/oc2p-img/src/main.rs`
  (kept out of the repo).
- Image `/tmp/oc2p-kf01/metaos-bios.img`: 17269760 bytes, valid MBR (`0x55AA`,
  `file` reports DOS/MBR boot sector + partitions).
- Verbatim: `/tmp/oc2p-kf01/OC2P-kf01-image.txt`.

## OC2P-003 BOOT — BOOT (not FAIL; no-boot-status honestly N/A)

- QEMU: `-drive format=raw,file=metaos-bios.img -display none -no-reboot -m 512M
  -serial file:serial2.log -monitor unix:...` — kernel alive at ~4s.
- Alive line PRESENT 1x: `META OS KERNEL - alive (K1)`.
- Full init on serial: `mem summary: K4 up`, `HELLO FROM USERSPACE`,
  `user exit code 0` x3, `task killed`, `user readkey: entry`,
  `sleeper: bad call refused`; zero `loader refused`/panics/triple-faults.
- Interactive proof via existing `os-build/tools/drive.py` attach (typed `help`,
  `status` over sendkey): `commands: status help` 1x,
  `STATUS tasks=8 ticks=5507 heap_free_kb=255` 1x — shell live, 8 tasks.
- Framebuffer field presence FROM BOOT OUTPUT: PRESENT — bootloader stage INFO
  lines: `Framebuffer info: FrameBufferInfo { byte_len: 2764800, width: 1280,
  height: 720, pixel_format: Bgr, ... }`, `BiosFramebufferInfo { region:
  fd000000 len 2a3000, 1280x720 Bgr }`, `Map framebuffer`. Kernel serial prints
  no framebuffer line of its own (consistent with KF-03 wiring still owed).
- Screendumps `OC2P-kf01-fb0/fb1.png` (sips-converted from 1280x720 PPM, identical
  md5): screen shows the bootloader handoff log frozen at
  `Jumping to kernel entry point` — kernel VGA-text writes go to the undisplayed
  0xB8000 text buffer while the pixel framebuffer is active. KF-03 known gap,
  not a boot failure: serial proves the kernel runs to interactive shell.
- Serial logs: `/tmp/oc2p-kf01/serial.log` (first boot, 50730 B),
  `/tmp/oc2p-kf01/serial2.log` (evidence boot incl. drive.py exchange, 50902 B).
  Verbatim boot notes: `/tmp/oc2p-kf01/OC2P-kf01-boot.txt`.

## OC2P-004 — not invoked (no instruction to restore/patch)

- Report only: { built: YES, imaged: YES, booted: YES }.
- No 0.9.35 restore attempted; no kernel source touched; nothing committed/pushed.
