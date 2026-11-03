# Milo QA audit — merge-layers pre-step (2026-11-02 ~23:50 EST)

Scope: independent QA/security audit slice, NOT gate-1 (gate-1 stays with
the rust-work loop). Audited tree: origin/main @ e43e486d (Pax lane
merge of opencode1/metaos-1.0 frozen contracts + theme stack).
Trigger: Pax room-1 QA target 23:41 EST — "merge-layers pre-step first,
it is the only auditable target until base ISO bytes land on the build
host; first-ISO-candidate QA waits on that."

Labels: VERIFIED / CODE-INSPECTED / BLOCKED / UNIMPLEMENTED (per the
12H plan's proof discipline; missing is named, never padded).

## 1. Current state — UNIMPLEMENTED as code, spec on record

No merge-layers script exists anywhere on main (grep over
`os-build/iso/` and the tree finds only references to the missing step):

- `os-build/iso/build_iso.sh` `--iso` mode: the `layered)` branch dies
  with "merge the layers first", and `--base-info` prints "merge layers
  (out of scope)". The script refuses a layered base rather than
  patching the wrong file. That refusal is correct behavior, not a bug.
- `os-build/iso/BASE_FACTS.md` (Buffy, merged): the reference Xubuntu
  24.04.5 image is LAYERED (minimal + standard + live squashfs,
  9.68 GB assembled, no single `casper/filesystem.squashfs`), and
  option B — merge layers at build time — is the recorded
  recommendation. "It is not built yet; this file records the
  measurement, not a claim that it works."
- `os-build/iso/PAX_BLOCKERS.md` (Buffy): same option B, same status —
  "Until this is decided, H+8 cannot start even with a Linux host."
- `os-build/METAOS_1.0_RELEASE_CHECKLIST.md` cut-1 record: "Buffy's
  lane task: a merge-layers [pre-step]". It is Buffy's build task;
  this audit does not build it, it gates it.
- `os-build/iso/calamares/modules/unpackfs.conf`: Calamares `unpackfs`
  takes exactly one source, `/cdrom/casper/filesystem.squashfs`, and
  "cannot join layers" — so the merged root is on the critical path
  for any Calamares install claim, not optional polish.

QA verdict on the pre-step itself: UNIMPLEMENTED. No merge claim is
made here, and no merge is claimed to have been tested.

## 2. What the pre-step must do — CODE-INSPECTED spec (from BASE_FACTS)

When Buffy's merge step lands, QA will check it against these
already-recorded requirements, not against a fresh invention:

1. Layer order, exact: `minimal.squashfs` THEN
   `minimal.standard.squashfs`. The `.live` layer is live-session
   only and is NOT installed — including it would be a wrong-root
   defect, not a superset.
2. Merged root size: 5,833,063,872 bytes uncompressed per BASE_FACTS
   (layer sizes sum byte-exactly to `filesystem.size` per
   PAX_BLOCKERS). A merge whose root size does not reconcile to that
   figure fails QA until the difference is explained.
3. Output: one `casper/filesystem.squashfs`, provisioned, repacked;
   `install-sources.yaml` rewritten to a single source pointing at
   it. Until that rewrite lands, `build_iso.sh --iso` will still die
   on the `layered)` branch — that die is the tripwire proving the
   pre-step ran or did not.
4. Base hash gate preserved: `build_iso.sh verify_base` checks the
   base SHA-256 BEFORE any extraction, and opting out is explicit
   and logged. The merge step must not bypass that gate (no merge of
   an unverified download, no silent `--no-verify-base`).
5. Host requirements, already recorded: Linux + root + ~12 GB free
   in the work dir; tools `xorriso`, `unsquashfs`, `mksquashfs`,
   `chroot` (the same set `build_iso.sh --iso` already demands).
   A merge run claimed from any other host shape fails QA.
6. Downstream proof still owed after a merge lands: `build_iso.sh
   --iso` must then take the `single)` branch (not `layered)`),
   Calamares `unpackfs` must consume the merged root, and the VM
   boot-to-login proof must follow. The merge alone proves nothing
   about boot, login, desktop, apps, or autostart.

## 3. Execution — BLOCKED (no base ISO bytes on this host)

- No `*.iso` exists in this VM's workspace or in the worktree
  (checked 23:50 EST). The checklist cut-1 gap stands verbatim:
  "the base Xubuntu ISO file is Del's own download; the byte-build
  starts when the file reaches the build host."
- Consequence, per Pax's 23:41 target: first-ISO-candidate QA waits.
  This audit is CODE-INSPECTED only. No merge was executed, no
  squashfs was unpacked or repacked, no VM was booted, $0 spent,
  no live key used, no live call made.
- Del's 23:35 1.0/2.0 directive status, per Pax 23:41: Pax is NOT
  treating it as a confirmed change of orders and has escalated it
  to Del; Hana holds her current lane until Del confirms. This
  audit follows Pax's current QA target (this pre-step) and takes
  no position on the directive beyond noting Pax's escalation.

## 4. Also confirmed this run (no action, monitor only)

- origin/main advanced 3142f841 -> e43e486d during this run: Pax
  lane merge of opencode1/metaos-1.0 (frozen contracts +
  theme stack, 20 files, +217). No merge-layers code in that delta;
  no build_iso.sh change. Monitor only — Pax merges only.
- MT-08 register already carries Pax's 23:41 cut-1 line verbatim in
  substance (doc/config N/A, loader script GREEN, K4/KF-03 HELD
  with reasons named), recorded on milo/test-slice-prep @ 799974be
  in the 23:28/23:33 run. No duplicate register edit made here.
- Main bus: NO_NEW. Room-1 tail re-read verified no missed
  directive beyond the Pax QA-target + posts-clarification items
  acted on here (crew room-1 completion posts continue per standing
  order; only-Pax-posts means release posts and merges to main).

## 5. Owed next (to Pax)

- Buffy's merge-layers step itself (build task, not QA).
- Base ISO bytes on the build host (Del's download, per checklist).
- Pax's next QA target after this pre-step audit, per the sleep
  order ask in the room-1 completion post for this slice.
- Standing items, unchanged: pair-swap/ipc2 Mac boot logs + Pax
  merge calls; Buffy L1-L5 proof on main; KF-03 Mac/Buffy re-proof;
  K3 re-gate/gate-2; framebuffer screendump; toolchain report;
  Del key-route pick + 402 top-up (live-key steps only).
