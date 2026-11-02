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
- Missing from stock image (task 11 backlog): node, git.

| # | Task | Status | Artifact |
|---|---|---|---|
| 1 | Boot carrier image, record numbers | TODO | — |
| 2 | Spike A: kiosk web shell | TODO | — |
| 3 | Spike B: real desktop (openbox class) | TODO | — |
| 4 | Judge + pick | TODO | — |
| 5 | Decision in STATUS.md | TODO | — |
| 6 | Scaffold os-build/face/ | DONE | this dir + build-image.sh |
| 7-13 | Image foundation | TODO | — |
| 14-17 | Boot screen | TODO | — |
| 18-21 | Login | TODO | — |
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
