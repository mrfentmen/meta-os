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

## Section 8 — Science cycle 1, Delaney reproduction (OC2B-176–200) — DONE 2026-11-02
- Target (named first): Delaney solubility cross-check (`labs/delaney-xcheck`), expected RMSE 1.099 ± 0.05 from repo-recorded numbers. Falsifier: RMSE outside [1.049, 1.149] kills the claim.
- Prereg hash committed BEFORE any run (commit `4c63aa8` precedes all result commits). Inputs frozen + hashed. Deterministic run.py, seed 500001.
- Verdict MATCH (all fields in band), critic answered with evidence, clean-dir re-run bit-for-bit, level L3 (independently reproduced, justification in record).
- Pack `labs/cycles/cycle-001/` complete (record/prereg/inputs/run/raw/score/critic/verify/summary/second-eyes/pack.sha256 + figure). Ledger entry quoted in record. Suite re-run 177 OK. No summary above earned L3. Spend $0 (no model calls). Pack hash recorded.
- Bond checklist: re-run run.py from inputs/, compare raw/ hashes, check verify/rerun_result.json bit-match, confirm critic response cites evidence.
- Truth: cycle-001 reproduced the repo-recorded Delaney prep statistics exactly as pre-registered. Landed. Nothing blocked.

## Section 9 — Science cycle 2, different department (OC2B-201–225) — DONE 2026-11-02
- Target (named first): physics projectile range (textbook value, different department from chem cycle-1). Falsifier + prereg hash committed first (same `4c63aa8` prereg commit).
- Verdict MATCH, critic answered, clean-dir re-run bit-for-bit, level L3. Full pack `labs/cycles/cycle-002/`. Suite 177 OK. Spend $0.
- Truth: cycle-002 reproduced the textbook range inside its pre-registered band. Landed. Nothing blocked.

## Section 10 — Science cycle 3, model-directed (OC2B-226–250) — DONE 2026-11-02
- Spark directed (prompt+reply+receipt under `model/`); adopt/reject lines in record. Falsifier + prereg first.
- Wonder read the cycle figure (agreement recorded with exact numbers); SAM segmented one labs image (box+overlay recorded, no-box would have stood as-is); critic came from the second model; `model/impact.md` states per-call what changed (model direction changed nothing — runs were deterministic).
- Verdict MATCH, clean-dir re-run bit-for-bit, level L3. Pack + figure + pack hash complete. Spend from receipts (small, metered-only). Suite 177 OK.
- Truth: cycle-003 matched under a model-written plan that changed nothing about the outcome. Landed. Model flake noted (metered-but-empty responses filed honestly).

## Section 11 — Cycles 4–5, repository + ledger hardening (OC2B-251–275) — DONE 2026-11-02
- Cycle-4 (shelf target): MATCH, L3, full pack. Cycle-5 (held-out Delaney rows-beyond-30 slice): DIFFER — recorded as failed reproduction with full completeness (failure.md names the first diverged input/step); level L2 per mismatch cap, even though the clean re-run agrees bit-for-bit.
- Repository export of all 5 packs (paths + hash-check table in `OC2B-repository-export.md`). Ledger audit (`OC2B-ledger-audit.md`): 5 entries, levels 3/3/3/3/2 match records. Ladder grep audit: no export/summary above earned level.
- `labs/cycles/COMPARISON.md`: 5-cycle table + DIFFER honour roll (cycle-005 listed unedited).
- Suite 177 OK. Spend $0 outside cycle-3 receipts.
- Truth: four reproductions at L3 and one honest DIFFER at L2, all hash-chained and exported. Landed. Nothing blocked.

## Section 12 — Hortus run 001, eight generations (OC2B-276–300) — DONE 2026-11-02
- Entry map + suite baseline (14 OK) in `labs/hortus/runs/run-001/record.md`. Definition + seed 500001 BEFORE run (pop 20, nominal fitness).
- 8 generations logged (best 47.37→108.84, mean 34.79→88.88, one mean dip at gen 7 — reported, not smoothed). Curve figure in pack. Clean-dir rerun byte-identical.
- Selection: max fin area past mass limit (34 fins @60mm, 0.51kg > 0.45 cap) → champion REJECTED by held-out gate (gate bites honestly).
- Pack hash recorded; run-002 change variable: POP_SIZE 20→40. CSV gap check: 8/8 rows. Suite re-run 14 OK. Wall time in record.
- Truth: run-001 selects hard under a biting gate and reproduces exactly. Landed. Nothing blocked.

## Section 13 — Hortus runs 002–003, selection analysis (OC2B-301–325) — DONE 2026-11-02
- Run-002 (pop 40, one variable changed): best 56.59→115.78 monotone; selection tall thin-fin area inside cap (33 fins, 0.39kg) → verified-candidate. Run-003 (calibrated low-h env fitness): best 17.35→38.02 then flat gens 6–8 (plateau reported; scores not cross-comparable by construction) → verified-candidate.
- COMPARISON.md: 3-run table, diversity metric (mean pairwise normalized Euclidean: 001 0.7305→0.2233, 002 0.7579→0.2103, 003 0.7305→0.2257), collapse NO/NO/NO (<0.05 threshold), 3 pack hashes, 5-line demonstrably-does chapter, total compute 0.03s, error lines (001: 2 pre-pack SVG errors with partials deleted, clean rerun; 002/003 error-free).
- Suites: hortus 14 OK, science-lab 177 OK (163 + 7 cycles + 7 hortus). CSV parse: 8 rows each, 24 total.
- Truth: Hortus breeds selectable, reproducible heatsink candidates under a held-out gate, capped at ladder level 2. Landed. Nothing blocked.
