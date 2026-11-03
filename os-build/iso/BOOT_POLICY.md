# VM boot policy (boss order, 2026-11-02)
- QEMU/UTM boots run ONLY on the high-RAM build Mac. Never on the 8 GB Macs.
- ONE booter at a time across all OpenCode agents. Coordinate before booting.
- Boots happen ONLY at meaningful milestones (e.g. desktop + apps working),
  never for routine checks. Static forensics, configs, and docs fill the gaps.
- Every boot: record ISO sha256 + serial log + framebuffer proof, or it
  didn't happen.
