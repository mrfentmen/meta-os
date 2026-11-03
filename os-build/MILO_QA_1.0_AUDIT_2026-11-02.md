# Milo QA audit — Meta OS 1.0 directive check (2026-11-02 ~23:40 EST)

Scope: independent QA/security audit slice, NOT gate-1 (gate-1 stays with
the rust-work loop). Audited tree: origin/main @ 3142f841 (B10 merge).
Trigger: Del/mrfentmen room-1 directive 23:36 EST — Meta OS 1.0 bootable
desktop tonight, custom Rust kernel as the 2.0 track; Milo = quality and
security, Pax = integration director / only merger.

Labels: VERIFIED / CODE-INSPECTED / BLOCKED / UNIMPLEMENTED (per the
12H plan's proof discipline; missing is named, never padded).

## 1. Directive vs plan — VERIFIED

`os-build/METAOS_1.0_12H_PLAN.md` already carries the directive's
division, verbatim in substance:
- Pax — integration + release, only merger. Rowan — kernel / 2.0 track,
  off the 12h critical path ("Nothing in the ISO waits on Rowan").
- Hana — base + first boot (Cubic, reference Xubuntu ISO).
- Buffy — boot + installer (Plymouth, Calamares).
- OpenCode 1 — login + desktop shell + theme. Bond — core apps.
- OpenCode 2 — agent layer packaging, autostart with `TryExec=`.
- Milo — audit + acceptance gates; "Milo gates nothing in motion";
  audits whatever exists at each cut, missing = BLOCKED.
No new architecture was invented for this audit; the directive tightens
the existing plan, it does not replace it.

## 2. Layered-ISO blocker — VERIFIED (code-inspected)

Del's claim: the reference Xubuntu 24.04.5 ISO is layered and
`build_iso.sh` refuses that structure. True, by design:
- `os-build/iso/build_iso.sh` `--iso` mode: `layered)` branch dies with
  "uses layered install sources (casper/minimal*.squashfs +
  install-sources.yaml); unpackfs and this patch path expect one
  casper/filesystem.squashfs. Use a base that ships it, or merge the
  layers first."
- `os-build/iso/BASE_FACTS.md` (Buffy, merged): reference is Xubuntu
  24.04.5, SHA-256 verified against Canonical's sums, LAYERED
  (minimal + standard + live squashfs, 9.68 GB assembled, no single
  casper/filesystem.squashfs).
- The script does NOT silently patch the wrong layer; it detects via
  `--base-info` first. The gap is the missing merge-layers pre-step
  (Buffy's lane task), not a silent-corruption risk.

## 3. No completed ISO artifact — BLOCKED (named, not stalled)

- `os-build/METAOS_1.0_RELEASE_CHECKLIST.md`, cut-1 record (main
  @0eddeb5d, 96/96 lane blobs verified): "the ISO artifact itself is
  not built — (1) The base Xubuntu ISO file is Del's own download;
  the byte-build starts when the file reaches the build host."
- Consequence, checklist's own words: "Proof: VM boot to login under
  60s — BLOCKED: no base ISO bytes exist yet."
- QA consequence: image integrity, boot logs, service health, login,
  desktop, apps, agent autostart, install-to-blank-disk, and checksum
  acceptance items are all UNPROVEN until an ISO exists. No ISO claim
  is made in this audit. First bootable image before desktop polish,
  per the directive, is the correct priority order.

## 4. Live-model 402 — VERIFIED, label stands

Checklist open blockers: "Meta API billing returned HTTP 402 on
2026-11-02 — live-model calls blocked." Per the directive, any release
record must label live model functionality unavailable; it must not be
reported as passed. This audit makes no live-model claim ($0, no key
used, no live call in this slice).

## 5. Secrets pattern scan — CODE-INSPECTED (limited)

Pattern scan of `os-build/iso/` for live-key / password assignments
(`sk-…`, `api_key = "…"`, `password = "…"`, excluding policy/example
text): no matches. This is a pattern scan of one lane directory only,
NOT a full-repo secret audit and NOT proof that no secret exists
anywhere in the tree. Full secret audit of a built ISO (no credentials
baked in, secrets generated at first boot) remains BLOCKED on the ISO
itself (see §3).

## 6. One clarification owed to Pax (not a blocker)

The 12H plan says "Only Pax pushes main and posts anything," while the
standing 5-minute work-loop order says Milo posts room-1 completions
and asks Pax for more tasks. This audit follows the work-loop order
(room-1 post only) and makes no public/release post. Pax to confirm
whether "posts" in the plan means release posts only.

## QA verdict for this slice

- Directive assignments: match the plan on file. No contradiction found.
- Layered-ISO blocker: real, correctly refused by the script, fix is a
  merge-layers pre-step (Buffy) + base ISO reaching the Linux build
  host (Del's download) + Pax's Linux host run.
- ISO acceptance (all 14 release items): BLOCKED on missing ISO bytes.
- Next QA target requested from Pax: the first ISO candidate (or the
  merge-layers pre-step) as soon as either lands, for image-integrity
  and boot-log audit. No further QA slice is started until Pax names it.
