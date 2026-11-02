# Face build — STATUS scoreboard (boss order 2026-11-02 02:21)

Spec of record: os-build/PREINSTALL.md + logo ruling (spinning blue
ASCII infinity ribbon; generated M dead). Every task ends PROVEN
or BLOCKED with the artifact named.

## Carrier image (Section 1, task 1) — PROVEN 2026-11-02

- Base: Debian 12 cloud image `debian-12-generic-amd64.qcow2`
  (448,790,528 bytes, qcow2, 3G virtual). The delivered image
  never arrived and os/build-image.sh needs root+Linux, so this
  recipe (os-build/face/build-image.sh) starts from the official
  cloud image + NoCloud seed. Boot log: face-boot1.txt.
- Boot: cloud-init finished, autologin as `relay` on tty1
  (screendump face-vga.png shows `relay@metaos:~$` with no typing).
- `systemd-analyze`: 7.859s kernel + 55.221s userspace = 1m03s
  (includes first-boot cloud-init; steady-state re-measured in
  task 17).
- Memory at idle: 1967M total, 249M used, 1718M available.
- Installed: 324 dpkg packages (stock cloud image).
- Hostname `metaos` ✓. Timezone America/New_York ✓.
  Locale C.UTF-8 (en_US.UTF-8 NOT generated — fix in task 10).
  Network ens3 10.0.2.15/24 dynamic, default route proto dhcp
  (DHCP proven, QEMU user-net).
- Missing from stock image (task 11 backlog): node, git. DONE via apt (node v18.20.4, git 2.39.5). Locale fixed (en_US.UTF-8). Updater: timer enabled, STOP honoured, real pull cycle proven — see image-status-2026-11-02.md.

| # | Task | Status | Artifact |
|---|---|---|---|
| 1 | Boot carrier image, record numbers | PROVEN | face-vga.png, face-boot1.txt |
| 2 | Spike A: kiosk web shell | PROVEN | spikeA-kiosk-guest.jpg, spikeA-notes-guest.jpg |
| 3 | Spike B: real desktop (openbox class) | PROVEN | spikeB-desktop-guest.jpg |
| 4 | Judge + pick | DONE | table below |
| 5 | Decision: **Spike A** | DONE | rationale below |
| 6 | Scaffold os-build/face/ | DONE | this dir + build-image.sh |
| 7-13 | Image foundation | PROVEN | image-status-2026-11-02.md, metaos-update.* |
| 14-17 | Boot screen | PROVEN | metaos.plymouth+script, boot-early/mid/late.png |
| 18-21 | Login | PROVEN | login-dark/shake/entered/light.png + AUTOLOGIN.md |
| 22-28 | Desktop shell | TODO | — |
| 29-33 | Wallpapers | TODO | — |
| 34-37 | Dock | TODO | — |
| 38-40 | Terminal | TODO | — |
| 41-43 | Dashboard | TODO | — |
| 44-49 | Systems as apps | TODO | — |
| 50-51 | Board | TODO | — |
| 52-59 | Everyday apps | TODO | — |
| 60-64 | First run + polish | TODO | — |
| 65-68 | Proof pack | TODO | — |
| 69-74 | Long tail | PARKED (after tonight) | — |

## Spike judgment (task 4) and decision (task 5) — DONE 2026-11-02

Evidence (all in os-build/face/, guest-rendered unless noted):
- `spikeA-kiosk-guest.jpg`: fullscreen chromium kiosk, live blue
  ribbon, top bar (∞ Finder, clock, NET/BAT/SND), dock.
- `spikeA-notes-guest.jpg`: real dock click opened a Notes window
  (titlebar, close button, top-bar app name switched).
- `spikeB-desktop-guest.jpg`: openbox + tint2 + lxterminal (real
  shell `relay@metaos:~$`) + pcmanfm (real files, 11.1 GiB free).
- `spikeA-desktop-local.png`, `spikeA-terminal-local.png`: the
  same shell in a desktop browser (terminal window open).

| Criterion | A: kiosk web shell | B: openbox desktop |
|---|---|---|
| Time to desktop | ~12 s (chromium first paint) | ~20 s (WM+panel+4 apps) |
| Mock fidelity | HIGH: pixel-exact bar/dock/windows, live ribbon canvas, light/dark = CSS | LOW: stock decorations, manual tint2 theming |
| Real apps | Launcher daemon (POST+subprocess, proven pattern); terminal needs a pty bridge (gap, named) | Native: every app real today |
| Effort to finish | Shell done; harden launcher, add pty bridge + files route | Theme everything to mock quality (big) |

PICK: **Spike A**. Fidelity is the hard requirement (approved
mocks, "Mac polish"); B's realness gap closes with small
localhost services — facts (done, live numbers), launcher
(done), pty bridge + files route (Sections 5/8 work). The
pty-terminal gap is stated, not hidden. Pax may overrule within
one cycle; silence = proceed.

## Section 3 — boot screen (tasks 14-17) — PROVEN 2026-11-02
- Theme `metaos` (plymouth script plugin): black screen, 20-dot
  blue orbit ring computed live per refresh, thin blue progress
  bar bound to real boot progress, three white stage lines naming
  the real stages (kernel -> rootfs -> face). No pre-rendered
  video: every moving pixel is computed at boot.
- Screendumps: boot-early.png (dots at ~2 blocks), boot-mid.png
  (dots rotated = animation proven across frames, bar ~19/20),
  boot-late.png (splash quit, autologin prompt).
- Boot-to-login measured: 11.848s kernel + 29.329s userspace =
  41.178s, inside the 45 s budget (after trimming cloud-init
  per-boot services + e2scrub_reap; first-boot cloud-init cost
  excluded as one-time).
- Honest note: plymouth forces text mode when a serial console is
  present, so the SHIPPED kernel cmdline drops `console=ttyS0`
  (keeps `console=tty0`). Serial logging is a dev-time variant
  (add it back on the GRUB line); shipped proofs use screendumps.
