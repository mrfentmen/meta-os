# ISO lane status — Bond (was Buffy), 2026-11-02

Two lanes from `METAOS_1.0_12H_PLAN.md`: **boot + installer** and **core apps**.
Everything below is on branch `bond/12h`, committed, checked, and labelled.

## RK-007 — boot proof: BLOCKED on this machine

| Step | State |
|---|---|
| userspace ELFs (hello/sleeper/crasher/readkey) | BUILT on `bond/rk007` |
| kernel ELF (`metaos-kernel`, bootloader_api 0.11.17) | BUILT, 4.8 MB, no errors |
| host-side image builder (`os-build/layer1/rk007-builder`) | **COMPILED, image produced** — 6,784,000 bytes, boot sector ends `55aa` |
| boot in QEMU | **BLOCKED** — no QEMU on this Mac, and the boss ruled out running it here |

The 0.11 flow is confirmed by the build itself: `bootloader_api` is the only
kernel dependency and the host `bootloader` crate supplies BiosBoot. The
builder needs `nightly`, `rust-src` **and `llvm-tools-preview`**. All three are
present here now; the third was missing until this run, and without it
`bootloader`'s build script dies with `failed to get llvm tools: NotFound`.

To finish RK-007, someone with QEMU runs:

```sh
cd os-build/layer1/rk007-builder && cargo +nightly build
./target/debug/rk007-builder ../../../kernel/target/x86_64-unknown-none/debug/metaos-kernel /tmp/metaos.img
qemu-system-x86_64 -drive format=raw,file=/tmp/metaos.img -nographic -no-reboot -m 512M
```

and files the serial log verbatim. No kernel code was touched; nothing was patched.

## Measured 2026-11-03: the builder works, the boot is what is missing

Run on this Mac, in `os-build/layer1/rk007-builder`:

```
rustup component add llvm-tools-preview --toolchain nightly
cargo +nightly build                     # Finished dev profile, 0 errors
./target/debug/rk007-builder \
  ../../../kernel/target/x86_64-unknown-none/debug/metaos-kernel \
  /tmp/metaos-rk007.img
# rk007-builder: image /tmp/metaos-rk007.img (6784000 bytes)
```

The artifact is a real BIOS disk image: it opens with `31 c0 8e d8 8e c0`
(clear ax, load the segment registers) and its first sector ends `55 aa` at
offset 510, the boot signature the firmware looks for.

What this proves: the kernel ELF, the host-side builder crate and the 0.11
BIOS stages all work together, and an image can be produced from source on
this machine. What it does **not** prove: that the image boots. That needs
QEMU, which this machine does not have.

Two defects were found by running it instead of reading it:

1. The builder called `create_disk_image(path)` and then `.display()` on the
   result. That method returns `()`, so the crate had never compiled.
2. `llvm-tools-preview` was not installed, so the bootloader build script
   panicked before the builder's own code was ever reached.

Both are fixed on `bond/rk007`. The image is a build artifact and is not
committed. Commands above assume the kernel ELF was built first.

## H+2 — Plymouth splash: CODE-INSPECTED

`iso/plymouth/metaos/` — descriptor, script, ring asset. One blue ring and the
name on ink black, pulsing with real boot progress. **Not booted**: no proof
that it draws. The base lane's H+2 VM run produces that evidence.

## H+8 — preseeded installer: CODE-INSPECTED

`iso/calamares/` — branding, slideshow, module order, and presets for
partition (erase disk, ext4, no swap), users (no autologin, 12-char floor,
sudo), welcome (storage + RAM only), locale (America/New_York).
**Install never run.** The H+8 acceptance line stays UNPROVEN.

## H+6 — core apps: CODE-INSPECTED

`iso/apps/` — four launchers (Files, Terminal, Settings, Web), four Plank dock
items, a Chromium policy, and a start page that renders with no network.
**Not clicked in a live session.**

## The check that did run

```sh
python3 iso/tools/check_iso_config.py
# 33 passed, 0 failed, 0 skipped
```

It parses every YAML/INI/JSON file, checks that every image and .desktop the
configs name exists, that module names are real Calamares modules, that the
password floor is 12, and that the start page loads nothing remote. It is a
file-level check and says nothing about a running system.

## What is owed, by name

- RK-007 boot + serial log + screendumps — needs a QEMU machine.
- Plymouth visible on a real boot — needs the base VM.
- Clean install to a fresh disk, rebooting to the login screen — needs the VM.
- Each app opened from the dock and closed clean — needs the VM session.

## Amendment adopted — build to the frozen contract (d835b59a)

The plan's decoupling amendment says Bond builds pages to `tokens.json`, never
to OpenCode 1's CSS. That is now true here:

- `iso/contracts/tokens.json` is a vendored copy of `metaos-contracts/tokens.json`
  at `opencode1/metaos-1.0` `953b41f4`, pinned by sha256 in `iso/contracts/PIN.md`.
- `iso/tools/tokens_to_css.mjs` generates `iso/apps/chromium/tokens.css`; the
  start page links it and carries **no hex of its own**. The checker fails if the
  CSS is stale or the page grows a raw colour.
- The splash and the installer sidebar now use the same contract values
  (`#070B16`, `#EDF5FF`, `#1877F2`), so one ISO does not ship two palettes.

The frozen app set has five IDs. Four ship. `agent-status` has **no binary on
main**, so no launcher is shipped for it — named BLOCKED in `iso/apps/README.md`
rather than a `.desktop` pointing at nothing.
