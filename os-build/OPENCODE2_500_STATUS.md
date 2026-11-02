# OPENCODE2 500 — status file (one block per section)

Branch: `opencode2/500`. NEVER push main. Pax merges at checkpoints.
Base: main `2b153988` (B10 merge @8a262b0f, Milo GATE-1 GREEN).
API rule: key tried once per call, logged once, offline path taken, no retry-loops.
Spend guardrail: cumulative model spend stays under Del's cap; every live call saves its receipt.

## Section 1 — Baseline (OC2B-001–025) — DONE 2026-11-02

- OC2B-001: branch `opencode2/500` from main `2b153988` (`git branch --show-current` prints opencode2/500).
- OC2B-002: wave-1 science parity: `git diff f49dc51d main -- os/worlds/science-lab tests/science-lab` is EMPTY (clean — merge 5e6b5191 was file-complete). `git ls-remote` shows `origin/opencode2/science-lab` at `f49dc51d`.
- OC2B-003: wave-1 sections: 1–10 COMPLETE (163 tests green on execution branch, ledger 20 entries verified, exports audit 14 claims 0 violations). No partial sections. Carried UNPROVEN (remote adapters, live paper extraction TO_BE_READ_AT_RUN, model judgement calls, L4-6 automated, SAM/Image live proofs) — inherited, not hidden.
- Baselines (tails committed under `os-build/logs/`):
  - OC2B-004 science-lab: 163 tests OK (`OC2B-baseline-science.txt`).
  - OC2B-005 hortus: 14 tests OK (`OC2B-baseline-hortus.txt`, engine 9 + calibration 5).
  - OC2B-006 queue: 289 tests OK (`OC2B-baseline-queue.txt`).
  - OC2B-007 goose node: 4 pass 0 fail (`OC2B-baseline-goose-node.txt`).
  - OC2B-011 kernel gate: GATE GREEN (`OC2B-baseline-gate.txt`).
- OC2B-008: key path `~/Desktop/hackathon key.txt` line 1 (48 chars) → SPARK_API_KEY env only. Model list from `server/queue/models.py` MODELS: muse-spark-1.3, muse-wonder-1.0, sam-3.1, muse-image-1.0, muse-voice-transcribe-1.0 (voice: listed, no verified surface). Grep of branch diff for key value: zero hits.
- OC2B-009: smoke chat via `models.chat_text(muse-spark-1.3)`: POST metered (65 tokens, $0.00023125, receipt in `OC2B-smoke-receipt.jsonl`) but response carried no message content → recorded OFFLINE-flake, 1 log line, zero retries. Receipt saved as ordered.
- OC2B-010: QEMU emulator version 11.1.3 (qemu-system-x86_64 present).
- OC2B-012: disk /dev/disk3s1s1: 926Gi total, 699Gi free — image work cleared (needs 20 GB).
- OC2B-013: python3 3.9.6, node v24.21.0, cargo 1.99.1, git 2.54.0.
- OC2B-014: `labs/cycles`, `labs/hortus/runs`, `labs/officina/builds` + READMEs committed.
- OC2B-016 guardrail: cumulative spend stays under Del's cap; receipts required per live call (§17 index, §20 grand total).
- OC2B-017: no new >1 MB files in §1 (logs are byte-scale; largest §1 addition < 100 KB).
- OC2B-018 model surfaces (from MODEL_INTEGRATION.md): (1) Spark chat POST /v1/chat/completions, in production since 2026-10-30 for assess. (2) Wonder chat same endpoint, probe reply WONDEROK ~2s. (3) SAM 3.1 POST /v1/responses, returns pixel box + encoded mask (chat refuses it). (4) Muse Image POST /v1/responses, returns image_generation_call base64 (chat refuses it). Voice transcribe NOT RESOLVED (404/model_not_found).
- OC2B-019 live-assess command (verbatim from LIVE_CAMS.md): `python3 server/queue/livecams.py --assess-one --area Brooklyn`.
- OC2B-020: `git diff main -- kernel/src` is EMPTY (untouched).
- OC2B-021 Node baseline (quoted, not re-run): `os-build/BOND_LIGHT_LANES_REPORT.md` — npm test this tree 2048 tests / 1993 pass / 55 fail (native/Swift); `os-build/MAC_RUN_REPORT.md` — npm test 1967 passed 0 failed.
- OC2B-024 Mac-only dependency table: QEMU 11.1.3 present | key present (flaky, offline fallback) | disk 699Gi free | pretty_midi NOT YET installed (§19) | goose toolchain path checked §19 (services/BUILD.md).
- OC2B-025 baseline index: OC2B-004 science 163 OK | OC2B-005 hortus 14 OK | OC2B-006 queue 289 OK | OC2B-007 goose-node 4/0 | OC2B-011 gate GREEN. Fixed numbers for later sections.
- Landed: branch, parity, baselines, env, dirs. In flight: none. Blocked: smoke-chat message content (metered-but-empty flake; offline path used downstream).

## Section 2 — KF-01/KF-02 support (OC2B-026–050) — DONE 2026-11-02
- OC2B-026/027: 0.11.17 std-fail reproduced in scratch worktree — MATCH (E0463 x6, serde_core, 41100-line log). No image, no screendump (honest).
- OC2B-028/029: 0.10.9 API-fail reproduced twice — MATCH (E0433 x2 verbatim, 15 errors). No image, no screendump.
- OC2B-030/031: candidate = 0.10.9 (no newer version named anywhere). BootInfo framebuffer YES (`pub framebuffer: Optional<FrameBuffer>`, bootloader-0.10.13 registry source). No image, no candidate screendump.
- OC2B-032: cross-check table `OC2B-kf01-table.md` stands.
- OC2B-033–038: BLOCKED re-verified — no upgraded-stack branch exists (only spike pins 0.10.9; all rowan/* pin 0.9). No gate/boot/shell/badsyscall/isolation/timing fabricated.
- Landed: KF-01 reproduction + candidate field proof. In flight: none. Blocked: KF-02 upgraded stack (waiting on Rowan).

## Section 3 — KF-03–KF-08 screendumps and fallback (OC2B-051–075) — DONE 2026-11-02
- All UNLANDED: `mod framebuffer` = 0 in kernel/, no put_pixel/GOP/fill drivers (`logo_frames.rs` is ASCII text-console data, not pixel ribbon). Per-task absence notes in `OC2B-kf04-08.txt`.
- Screendump index: zero captures, zero sha claims, zero mismatches (honest). No panic occurred (no boots exist) — no PANIC pair fabricated.
- Landed: absence verification. In flight: none. Blocked: framebuffer wiring (KF-03), pixel text (KF-04), boot-line re-render (KF-05), ribbon (KF-06), phases+keypress (KF-07), fallback (KF-08) — all waiting on Rowan.

## Section 4 — KF-09/KF-10 windows + Milestone 1 pack (OC2B-076–100) — DONE 2026-11-02
- All UNLANDED: no window/desktop/topbar/dock code in kernel/ (sole "window" hit is a sched.rs comment). Per-task notes in `OC2B-kf09-11.txt`; absence rows in screendump index.
- No Milestone-1 pack assembled (no single tree with serial+ribbon+shell exists). kernel/ diff vs main EMPTY (verified). 3-line Pax summary in status per task OC2B-100: KF-01 failures reproduced MATCH on second machine; candidate 0.10.9 carries Optional<FrameBuffer>; everything past KF-01 waits on Rowan's upgraded stack + framebuffer wiring.
- Landed: absence verification + Pax summary. In flight: none. Blocked: full waiting-on list above.
