# OC2 PROOF LANE — `opencode2/proof` (rolling)

Motto: every claim boots or it didn't happen. Standing lane for turning the
12-hour program's specs into boot proofs. Commit per task batch; push per section.
Fences: NO kernel edits (Rowan's pen, syscalls.rs FROZEN). NEVER push main.
No mock as done. Secrets never in files. Pax merges; Milo audits.

## Standing triggers (check at session start, in order)
- T1 Rowan rewrite watch: `git ls-remote origin rowan/bootloader-spike`. If it moves
  past a filed state, build/boot/screendump it in a scratch worktree, file verdict.
- T2 Hana base watch: any `*.iso`/`*.qcow2` on main or a bootable-base branch → re-run
  the agent-autostart acceptance on it (same recipe as OC2-proof, Phase D).
- T3 Buffy ISO watch: any installable image → attempt install-to-disk proof (record only;
  installer is Buffy's lane — proof, never patch).
- T4 Cross-check: one OpenCode 1 proof per session, AGREE/DISAGREE with evidence.

## Task list (proof per task; BLOCKED with the exact missing piece, never faked)

### S1 — KF-01 corrected attempt (fires on T1; ACTIVE NOW — 717e7ffb landed)
- OC2P-001: build `rowan/bootloader-spike @717e7ffb` (RK-008 pin + rewrite) in a scratch
  worktree, nightly flags from gate.sh. Verbatim build log → `os-build/logs/OC2P-kf01-corrected-build.txt`. PASS = kernel object produced. FAIL = verbatim errors filed, stop per correction rule.
- OC2P-002: if OC2P-001 passes, build the host-side boot image (smallest tool using the
  0.11 `bootloader` crate BiosBoot/UefiBoot path per RK-008 step 6 — tooling, in scratch,
  never committed as product). Verbatim log.
- OC2P-003: boot it in QEMU, serial + screendump set (`OC2P-kf01-fb*.png`), alive line,
  framebuffer field presence from boot output (not source). Verdict: BOOT or FAIL-with-logs.
- OC2P-004: if OC2P-003 fails with logs AND no Rowan pick exists: restore 0.9.35 pin in a
  scratch tree, re-run gate.sh GREEN 7/7, file evidence, stop. Route call is Pax's.
- OC2P-005: section commit + status block (proven vs blocked, exact shas).

### S2 — Agent autostart regression (per main move)
- OC2P-010: re-run the Phase-D fresh-boot proof recipe on latest main (units install,
  reboot, no-hand-holding check, assessed cycle, spend). USED to gate every `agent-layer/` change.
- OC2P-011: host-forwarded dashboard check (guest serves, Mac host curls the forwarded port).
- OC2P-012: GUI-base spike, bounded: ONE attempt to get a desktop in QEMU (Xubuntu ISO only if
  present locally — never download 9 GB on a hunch). Record or UNPROVEN-carry.

### S3 — Cross-check + closeout (every session)
- OC2P-020: one OC1 proof, AGREE/DISAGREE + evidence (film done; next: OC1 §7 soak or §19 rehearsal).
- OC2P-021: secrets sweep (zero hits required), >1 MB sweep, fence diffs (kernel/queue/registry empty).
- OC2P-022: status block + push; tip == ls-remote; tree clean.

## What this lane does NOT do
Kernel source, ISO assembly, installer fixes, base images, registry edits, model-pipeline
re-proofs (done), science re-runs (done — new cycles only on new backend evidence).
