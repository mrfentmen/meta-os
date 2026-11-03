# ISO lane status — Bond (was Buffy), 2026-11-02

Two lanes from `METAOS_1.0_12H_PLAN.md`: **boot + installer** and **core apps**.
Everything below is on branch `bond/12h`, committed, checked, and labelled.

## RK-007 — boot proof: BLOCKED on this machine

| Step | State |
|---|---|
| userspace ELFs (hello/sleeper/crasher/readkey) | BUILT on `bond/rk007` |
| kernel ELF (`metaos-kernel`, bootloader_api 0.11.17) | BUILT, 4.8 MB, no errors |
| host-side image builder (`os-build/layer1/rk007-builder`) | WRITTEN, stage crates compiled on nightly |
| boot in QEMU | **BLOCKED** — no QEMU on this Mac, and the boss ruled out running it here |

The 0.11 flow is confirmed by the build itself: `bootloader_api` is the only
kernel dependency and the host `bootloader` crate supplies BiosBoot. The
builder needs `nightly` + `rust-src`; both are installed.

To finish RK-007, someone with QEMU runs:

```sh
cd os-build/layer1/rk007-builder && cargo +nightly build
./target/debug/rk007-builder ../../../kernel/target/x86_64-unknown-none/debug/metaos-kernel /tmp/metaos.img
qemu-system-x86_64 -drive format=raw,file=/tmp/metaos.img -nographic -no-reboot -m 512M
```

and files the serial log verbatim. No kernel code was touched; nothing was patched.

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
