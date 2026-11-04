# Lane C — Installable media (arm64) — C_ISO_REPORT

Date (UTC): 2026-11-03. Owner: lane-C agent. Repo: `/Users/test/Desktop/meta-os`.
Timebox used: ~9 h wall (several build iterations; see incidents).

## C1. Architecture decision — arm64, one architecture ships — PROVEN

- **Base:** official Ubuntu 24.04.5 LTS desktop **arm64**
  `ubuntu-24.04.5-desktop-arm64.iso` (3,967,463,424 bytes).
- **Hash (verified against Canonical, not assumed):**
  `2be09ca883921bff6d8e6b0bfbafd13e32436553b7086f33bce3a4c5bad8bd14`
  exact match with `https://cdimage.ubuntu.com/ubuntu/releases/24.04.5/release/SHA256SUMS`
  (`grep desktop-arm64`). Recorded in `os-build/iso/BASE_FACTS.md` (arm64 section).
- **Reason:** the working MetaOS system (`/tmp/metaos.ext4`) is arm64 and boots
  on this Mac with `qemu-system-aarch64 -M virt -cpu host -accel hvf`. The amd64
  Xubuntu base (`/tmp/xubuntu-base.iso`) can only boot here under full x86
  emulation. The task forbids shipping two architectures; the working system is
  arm64, so arm64 is the one that boots tonight.
- **Consequence, stated plainly:** the amd64 Calamares lane (`merge-layers.sh`,
  first half of `BASE_FACTS.md`) is a *separate-build* record. No amd64 ISO is
  produced by lane C. The arm64 build reuses its merge strategy natively
  (host and rootfs both aarch64: no qemu-user-static).
- The arm64 base is layered like the amd64 one (`minimal.squashfs` 1.9 GB +
  `minimal.standard.squashfs` + `minimal.standard.live.squashfs`,
  `type: fsimage-layered`,
...[truncated 9113 chars]