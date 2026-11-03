# Buffy — boot + installer lane report

Written 2026-11-02 (late) for `os-build/METAOS_1.0_12H_PLAN.md`.
Branch: `buffy/boot-installer`, cut from `origin/main` @ `80a7886c`.
Lane ownership: Plymouth splash, Calamares preseed + Meta branding,
install-path testing in VM. Acceptance: ISO installs to a fresh disk and
reboots to the login screen, proven by VM screendumps.

## What exists now, and exactly what backs each line

| # | artifact | state | backing |
|---|---|---|---|
| 1 | `plymouth/metaos/metaos.plymouth` + `metaos.script` | WRITTEN, UNRUN | ini parses, script assets all exist, braces/parens balanced, no trig/loops/fonts (deliberate, so the untested script stays small) |
| 2 | Splash assets `logo.png`, `wordmark.png`, `dot.png` | GENERATED, VERIFIED LOCALLY | 512×512 / 480×120 / 24×24; sha256 in `assets/MANIFEST.json` and re-checked by the validator |
| 3 | Calamares `settings.conf` + 17 module configs | WRITTEN, UNRUN | all 19 files parse as YAML; 18 sequence modules map to a config file; instance config present |
| 4 | Preseed assertions | LOCAL-CHECK PASS | erase/no-swap partition, user `meta`, `allowWeakPasswords: false`, unpack from `/cdrom/casper`, no network installs, reboot pre-checked |
| 5 | Branding `branding.desc`, `stylesheet.qss`, 3 images | WRITTEN, UNRUN | productName MetaOS, images at 256/128/640×400, stylesheet present |
| 6 | `calamares/meta-branding.sh` (runs in target chroot) | WRITTEN, UNRUN | `sh -n` clean; path cross-checked against `provision.sh` and `meta-branding.conf` |
| 7 | `provision.sh` (host → chroot payload install) | WRITTEN, UNRUN | `sh -n` clean; installs theme, config, hook, autostart, initramfs rebuild |
| 8 | `build_iso.sh` (`--check`, `--root`, `--iso`) | WRITTEN, UNRUN | `bash -n` clean; `--check` runs here and reports the missing Linux tools honestly |
| 9 | `tools/qmp.py` | **PROVEN LOCALLY** | drove a real QEMU instance: `screendump`, `quit` |
| 10 | `tools/vm_install_proof.sh` | **PLUMBING PROVEN** (`--dry`), install path UNRUN | captured `proof/dry-harness/00-harness-dry.png` from a live QEMU framebuffer (720×400 SeaBIOS "no bootable device" screen, 4s after start) |
| 11 | ISO | **NOT BUILT** | no Linux host, no root, no xorriso/mksquashfs on this Mac |
| 12 | Install → reboot → login screendumps | **NOT RUN** | blocked on 11 |

Local validator: **36 pass, 0 fail, 0 skip** (`tools/check_configs.py`,
YAML parsed through ruby's psych because this Mac has no PyYAML —
no check was silently skipped). Shell syntax: 4/4 scripts clean.
Python syntax: 3/3 files compile.

## The one thing the boss must not misread

There is **no ISO and no install proof** in this report. What exists is a
complete, cross-checked config + build + proof toolchain, and one real QEMU
screendump that proves the harness can capture frames. The acceptance test
from the plan is still ahead of us and needs a Linux host with root.

## Why preseed is not "one click"

Calamares 3.x has no unattended mode and no key for a plaintext password.
Locale, keyboard, user name, disk layout, no-swap, reboot-on-finish are all
pre-answered; the operator still types the password and clicks Install.
That is a property of Calamares, not a gap I can close with config. The
honest acceptance run is `vm_install_proof.sh --iso … --keys … --reboot`
with `--vnc` available for the typed field; every stage is screendumped.

## Known risks (named, not smoothed)

1. **Plymouth script is unexecuted.** It is deliberately restricted (no
   trig, no loops, no fonts) to keep the untested surface small, but a real
   plymouth run is the only proof. If it misbehaves, the fallback is the
   `text` module; that is a 10-line change, not a redesign.
2. **Calamares version drift.** Module keys were written against 3.3-era
   config. Unknown keys are ignored by Calamares, but a renamed key would
   silently fall back to a default. First Linux run should print
   `/etc/calamares/settings.conf` module load errors before install.
3. **Base ISO is a parameter.** The plan names Xubuntu + Cubic; Hana's lane
   owns which point release. Both build paths work without knowing the
   flavour's own installer.
4. **Live-session user is copied by unpackfs.** Ubuntu flavours solve this
   with a post-install cleanup; MetaOS 1.0 does not yet. Cosmetic for the
   acceptance test (the new user logs in), but it should be closed before
   shipping a public ISO.
5. **`systemctl enable` inside the Calamares chroot** can warn on a system
   without dbus. It is logged to `/var/log/metaos-install.log` in the
   target, and step 6-7 of the hook fail soft with a WARN rather than
   producing a dead install; a boot-time check is still needed.

## What I need from other pens

- **Pax:** merge call on `buffy/boot-installer`; and the Linux host decision
  for the build+install proof (this is the only thing between us and the
  acceptance artifact).
- **Hana:** the base ISO point release and whether Cubic's chroot is
  reachable on her machine (path + whether root/network are available).
- **OC1:** confirm the greeter session name and where the theme package
  lands; the installer currently only enables LightDM and disables
  autologin, it does not theme the greeter.
- **Milo:** audit rows for items 1-10 above using the states I wrote; do not
  upgrade any of them to VERIFIED without the Linux run.
