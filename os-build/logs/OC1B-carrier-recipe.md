# OC1B carrier recipe survey (tasks 276-277, 280)

Date: 2026-11-02. Recipe: os-build/face/build-image.sh (54 lines).

## Current package set (OC1B-276)

The recipe installs NO packages. Its phases:
1. Fetch base: Debian 12 bookworm cloud image
   (debian-12-generic-amd64.qcow2, 448790528 bytes, qcow2, 3G virtual).
2. NoCloud seed: hostname metaos, user relay (sudo NOPASSWD), autologin
   on tty1, serial-getty on ttyS0. (seed.iso, 921600 bytes.)
3. Copy base -> metaos-face.img, qemu-img resize +10G (13G virtual).
4. Print sha256. Boot command documented (qemu, user-net, hostfwd :2222).
No apt installs, no node/git/chromium/opencode steps — the toolchain in the
live work.qcow2 guest (node v18.20.4, git 2.39.5, /usr/bin/chromium) was
installed live via apt per os-build/face/STATUS.md tasks 7-13, NOT by the
recipe. A fresh image from the current recipe is stock Debian + login config.

## Before-state (OC1B-277)

- Image: /tmp/face-img/metaos-face.img — 448790736 bytes, qcow2,
  13G virtual / 428M disk.
  sha256 f7d8581ebb05a8b708b9cc4252a50e1b90681cad684d5e8778a95951363167c3
- Four standing checks, last results on record:
  1. autologin tty1: PROVEN (face-vga.png shows relay@metaos, no typing).
  2. DHCP: PROVEN (ens3 10.0.2.15/24, default route proto dhcp — wave2-sec4 §2).
  3. dashboard/facts HTTP 200 live: PROVEN (curl localhost:18932 facts
     {"cpu","mem","disk","net"} live values; dashboard load numbers in
     guest screenshots — STATUS tasks 41-42).
  4. updater pull cycle: PROVEN (real pull cycle, timer enabled, STOP
     honoured — STATUS.md image-status-2026-11-02.md).
- Wave-2 finding carried: image has node + git + chromium; OpenCode ABSENT.

## Toolchain inventory block (OC1B-280)

Target (pinned in recipe header after the OC1B-278 edit):
  opencode 2.2.0 (pinned; installed by provision-toolchain.sh via the
    SST installer with version pin; verified `opencode --version` in guest)
  node: Debian bookworm nodejs+npm via apt (version recorded at build time)
  git: Debian bookworm git via apt (guest had 2.39.5)
  chromium: Debian bookworm chromium via apt (guest had /usr/bin/chromium)
  freebuff: ATTEMPTED via npm (freebuff@0.2.35); result recorded in this
    file's build section (Mac-only binary expected to fail on Linux).
Riders (already in recipe): hostname/autologin/serial-getty config.

## Build record (OC1B-279/281)

Three recipe iterations ran (all in /tmp/oc1b-carrier{,2,3}, base cached):

1. carrier1: provision failed loud — the v1 installer URL
   (https://opencode.ai/install) refuses 2.2.0 ("not an OpenCode 1
   release"). Fix: v2 installer URL (https://opencode.ai/v2/install
   with --version pin). No silent fallback.
2. carrier2: v2 installer downloaded 2.2.0, but the script linked the
   wrong path (~/.local/bin; real: ~/.opencode/bin/opencode) and the
   guest CPU (default qemu64, no AVX2) SIGILLed the Bun binary
   (`Illegal instruction`, line 27). Fixes: detect-and-link + `command
   -v` verify; `-cpu max` on provision + documented boot lines (proven:
   opencode v2.2.0 rc=0 under -cpu max; guest shows avx/avx2).
3. carrier3 (definitive): full base->provision run with final scripts,
   then a final-script idempotent re-run (rc=0, provision-final.log):
   opencode v2.2.0, node v18.20.4, git 2.39.5,
   chromium 156.0.8078.73, freebuff 0.2.35 installed AND running
   (`freebuff --version` -> 0.2.35, rc=0, under -cpu max with sudo npm
   prefix — the bare `npm i -g` EACCES was a harness permission, not a
   platform refusal).

Freebuff verdict (OC1B-279): INSTALLS CLEANLY — freebuff@0.2.35 via npm
runs on Debian amd64 (0.2.35, rc=0). The Mac-only assumption was wrong;
the npm package ships a working Linux binary. Recorded with output.
