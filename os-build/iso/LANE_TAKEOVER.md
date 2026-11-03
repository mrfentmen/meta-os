# Boot/installer lane: Buffy -> OpenCode 1 (2026-11-02, boss order)
Buffy reassigned to OS features. Her branch tip cbf00e3f preserved as
this branch's base; her measurement commits untouched, her name on them.

## Verification of her handoff (independent, same ISO hash 4ed869eb)
- Gate suite: PASS on this checkout (base-layout fixture all 4 hold).
- Layered sources, no filesystem.squashfs, no Calamares: CONFIRMED via
  own mount + manifest grep. Plymouth + LightDM present: CONFIRMED.
- Two nuances (tooling only, conclusions stand): (1) macOS CAN browse
  the ISO9660 wrapper (mounted, files read) — only squashfs contents
  need Linux; (2) her byte table mixes compressed on-disc sizes with
  uncompressed — additivity holds either way; uncompressed re-measured
  in Linux before sizing the merge work dir.

## Execution path chosen: option B via Docker (daemon up 2026-11-02)
Linux + root + 667 GB free on this Mac. Verifying layer order in
Linux now; then merge -> provision -> repack single filesystem.squashfs.
