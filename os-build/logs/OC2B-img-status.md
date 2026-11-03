# OC2B-126 — carrier-image STATUS read (Section 6)

Date: 2026-11-02. Branch: `opencode2/500` ( lane fence: no STATUS-file edits, no commits, no pushes; this log stands in for the §6 status block).

## STATUS source used

- Lane path `~/workspace/meta-os-image/STATUS.md` does NOT exist on this Mac (`~/workspace/` exists but holds only `hackathon/`; no `meta-os-image` dir).
- Repo copy used instead: `os-build/image-status-2026-11-02.md` (the face lane's four standing checks) plus `os-build/face/image/JOIN.note` (reassembly + expected hash).

## Recorded values

- Recorded sha256 (from `JOIN.note`, truncated prefix): `f7d8581e…` (full value not recorded in repo — prefix only).
- `os-build/image-status-2026-11-02.md` carries NO sha256 and NO PARTIAL list. Its four checks are all stated PROVEN: (1) autologin, (2) DHCP, (3) dashboard HTTP, (4) updater pull. Machine facts: hostname metaos, node v18.20.4, git 2.39.5, first-boot 7.859s kernel + 55.221s userspace, idle ~1967M total / ~250M used.
- PARTIAL items: NONE named in either file. Unproven list carried from §1 (remote adapters, live-paper TO_BE_READ_AT_RUN, model judgement calls, L4-6 automated, SAM/Image live proofs) is wave-1 science scope, not image scope.
- Repo image parts (`os-build/face/image/metaos-face.img.part-*`) are 0-byte placeholders — the image is NOT reassemblable from the repo alone. Live artifact found at `/tmp/face-img/metaos-face.img` (built 2026-11-02 06:47 by the face lane).

## Fresh shasum (OC2B-148, recorded here; STATUS file edit blocked by lane fence)

- Rebuilt 2026-11-02 with the lane script (see `OC2B-img-build.md`): `/tmp/oc2b-img-build/metaos-face.img`, 448,790,736 bytes.
- `shasum -a 256` → `f7d8581ebb05a8b708b9cc4252a50e1b90681cad684d5e8778a95951363167c3`
- Identical to the face-lane `/tmp/face-img/metaos-face.img` sha (byte-reproducible from the same base download). Matches the recorded `f7d8581e…` prefix. MATCH.
