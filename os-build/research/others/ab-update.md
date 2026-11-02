# A/B update design note (OS-114)

Borrowed from ChromeOS (verified boot) + NixOS (generations),
idea-only, no code.

- Two roots: A and B partitions (or two directory trees while the
  carrier is still Debian). Exactly one is live; updates write
  the IDLE side, never the running side.
- An update = a new generation: staged payload + manifest with
  versions (the pin step OS-010 owes), checksums, and the source
  commit. Nothing activates until the manifest verifies whole.
- Activation flips the boot pointer (GRUB default entry / target
  symlink) in ONE atomic step, then reboots into it.
- First boot of a generation runs the boot-proof set (Section N
  pipeline, K-level checks); on failure the pointer flips BACK
  and the failure is recorded. No half-updated machine ever
  serves traffic.
- Rollback = booting the previous generation. It is instant
  because nothing was overwritten — same property as NixOS
  generations, implemented as two roots instead of a store.
- What updates carry: whole generations (kernel + services +
  agents). No file-level patching, no `dpkg --configure -a`
  recovery path, no maintainer scripts running as root on a live
  system (rough edges 6, 3, 4 — answered structurally).
