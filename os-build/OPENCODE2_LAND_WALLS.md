# OC2 LAND + WALLS lane (opencode2/landwalls)

Purpose: turn specs + separate proofs into one bootable thing. Two tracks:
LAND = custom-kernel native path (Rowan pen — OC2 builds/boots/logs only, never edits kernel/).
WALLS = desktop ISO assembly proofs (support + cross-check only; Hana/Buffy/OC1/Bond own their lanes).
Rule for this lane: NO VM BOOTS until the demo target boots to the Meta spinning logo
with openable applications (boss order). Until then: static verification only.

## Standing watches (check every session, <2 min, no VM)
- T1 Rowan: `git ls-remote origin rowan/bootloader-spike rowan/kernel-k4-pair-swap rowan/kernel-k4-ipc2` — any move = support-test within 24h.
- T2 Hana base: any `*.iso`/`*.qcow2` on main or bootable-base branch = agent re-proof within 24h.
- T3 Buffy ISO: new `metaos-1.0.iso` bytes or install claim = clean-install witness review (read-only).
- T4 OC1 cross-check: one proof per session, AGREE/DISAGREE + evidence.

## S1 — KF-02 gate battery on 717e7ffb (support-testable NOW, highest leverage)
- OC2P-010: scratch worktree @717e7ffb; `gate.sh`-equivalent assertions against the new stack (alive, sleeper refused, task killed, shell answered, status ticks) — record GREEN/RED per line + full serial.
- OC2P-011: triple boot (3 serials, alive-line grep each) + bad-syscall-99 refusal + crasher-task isolation, all on the 0.11 stack.
- OC2P-012: file verdict (BOOT + gate transcript) or FAIL-with-logs; hand Pax the KF-02 call inputs. Do NOT attempt KF-03+ wiring (Rowan's code).
- Proof: `os-build/logs/OC2P-kf02-{gate,triple,badcall,isol}.txt` + serials. No kernel edits, no commits outside lane branch.

## S2 — k4 IPC verification (fires on Pax F1 ruling only)
- OC2P-020: build `origin/rowan/kernel-k4-pair-swap` (or -ipc2 per ruling) in scratch; run talker/listener transcript; verify send→recv no-loss + exit-funnel clear.
- OC2P-021: verify `bd4e003a` ipc.rs ring (Full/Empty/Closed, spawn_swap, no syscall numbers — frozen-table compliant) by code inspection + suite run if wired.
- Proof: transcript + verdict file. If Pax hasn't ruled, log "waiting on F1" and move on — never invent numbers.

## S3 — Agent autostart re-proof discipline (per main move)
- OC2P-030: fresh Debian guest (or Hana base when T2 fires): install.sh → reboot → journal pre-login proof → key handoff → assessed cycle + spend → reboot survival. Same bar as Phase D (no hand-holding, loud no-key pause, $ tracked).
- Proof: `os-build/logs/OC2-<base>-proof-*.{txt,json}` + status block. Reuse, don't rebuild, the agent-layer/ units.

## S4 — Dashboard forwarded + GUI spike (bounded)
- OC2P-040: host-forwarded dashboard check (guest serves :18900, Mac curls forwarded port). Record or UNPROVEN-carry.
- OC2P-041: GUI-base spike, ONE attempt max: Xubuntu 24.04.5 base ISO exists (5.2G, verified manifests, Xfce present, evince→atril mismatch noted). Attempt desktop reach in QEMU snapshot mode; screendump whatever appears. If no desktop in 30 min wall, file UNPROVEN + blocker, stop. Never download 9GB overlays.

## S5 — Cross-check + closeout (every session)
- OC2P-050: one OC1/Hana/Buffy/Bond proof, AGREE/DISAGREE + evidence file.
- OC2P-051: secrets sweep (zero hits), >1MB sweep, fence diffs (kernel/server-queue/registry empty).
- OC2P-052: status block + push (tip == ls-remote, tree clean).

## Upkeep — S8/S9 side batch (no VM, done 2026-11-03)
- [x] INSTALL-OC1 doc — `agent-layer/desktop-entries/INSTALL-OC1.md` exists, MANIFEST 16 paths.
- [x] 3 check scripts + tests green — keep-mime / manifest-targets / verify-dropin-desktop exit 0, suite 30/30.
- [x] WATCH/BLOCKERS live — `OC2P-WATCH.md` (4 watches), `OC2P-BLOCKERS.md`, links qualified.
- [x] Doc link audit clean — no bare validate.py/packages.txt/mimeapps.list/tokens.json/template refs.
- [x] verify-dropin backend fix kept — hard-FAIL with no sha backend, 64-hex regex.
- [x] Index appendices filed — `OC2P-proof-index-S8S9.md` rows 29-48, UNPROVEN-carry restated.

## Explicit non-goals (OC2 does NOT)
- kernel/src edits of any kind (Rowan). ISO/base/installer builds or fixes (Hana/Buffy). Registry, queue runtime, metaos-contracts edits. Model re-proofs while 402 stands. Feature work before W1 has bytes (trap #1). Re-proofs without new code (trap #2). Model-connectivity debugging (trap #3).
- Evince/atril KEEP mismatch: Hana's line — OC2 may only note it + propose the one-line ack in status, never edit her file.
- /private/tmp/isowork + mvm5 QEMU = another lane's live work. Read-only filenames, never touch, never boot it.

## AFK operating rules (carry over)
- Order: triggers → S1 → S2(if unblocked) → S3 → S4 → S5. No VM 06:00-22:00 local unless a proof strictly requires fresh boot; batch VM work for sleep hours; cpulimit any daytime QEMU.
- Before EVERY commit: side effects restored, status clean, size-check, fence diffs.
- Wake-up report: tip sha + per-section verdicts + suite totals + UNPROVEN list.
