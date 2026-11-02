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

## Section 14 — Officina 2b prior-art (OC2B-326–350) — DONE 2026-11-02
- Baseline: 49 tests OK + 2a gate 14/14 (in `OC2B-officina-baseline.md`). Bounds read live from `heatsink.py:51,54` (FIN_HEIGHT (5.0,80.0), BASE (2.0,12.0)).
- 2b `prior_art.py`: note schema (sources mandatory), zero-source rejection, repo grep search (capped 2 hits/file), web search (URLs+titles), per-claim sources, forbidden-phrase strip-guard, 2a→2b wiring.
- Briefs A (heatsink-fin fixture), B (rough-words bracket), C (fin-array variant) → notes with primary/secondary marks, dead-URL re-fetch column, dedup clean. 3 timings recorded. Offline drill: repo-only note (clean refusal path tested).
- Suite + gate re-run green. Stage record `OC2B_OFFICINA_2B.md`. Registry proposals as status text (not made).
- Truth: 2b writes sourced prior-art notes and never a patentability opinion. Landed. Nothing blocked.

## Section 15 — Officina 2c packs + 2d memory (OC2B-351–375) — DONE 2026-11-02
- 2c `pack_export.py`: emitter + `check_pack` against live bounds. Checker tests: at-bounds pass, +1mm-over fails naming field, base-bound direction documented. Packs A/B/C emitted, all check ok in-workdir and clean-dir.
- 2d `memory.py`: append-only JSONL (format in docstring). Tests: append/read-back, two-brief readability, 50-append oldest-present. Backfill 3 packs. Read-back dump + truncation drill (fails clean with line number) in `OC2B-2d-readback.md`.
- Suite 77 OK + gate 14/14. Stage records `OC2B_OFFICINA_2C.md` / `2D.md`. Proposals as status text.
- Truth: packs carry in-bounds dimensions and memory never drops entries. Landed. Nothing blocked.

## Section 16 — Two real builds (OC2B-376–400) — DONE 2026-11-02
- Build-001 (rough-words fanless router sink, no numbers): 2a proven R 1.7210 (4 rounds) → 2b note → 2c pack (15 fins, 4.0mm 50×50 base) → bounds ok (independent clean-dir PASS) → faber gap recorded verbatim (loop takes loop seeds, not packs — no forcing) → memory seq 3 → GENERATED render (webp, magic-verified, receipt parses) → summary.
- Build-002 (different object, forced-airflow): 2a proven R 1.0623 (2 rounds) → same chain → memory. COMPARISON.md: identical vs differed, memory oldest-first, per-stage timings, no hidden failures.
- Scripted no-OOB check over ALL packs: clean. GENERATED filename list: one file (build-001 render).
- Suite 77 OK + gate 14/14.
- Truth: Officina turns rough words into checked packs and remembers them; nothing built physically. Landed. Nothing blocked.

## Section 17 — Model pipeline live proofs (OC2B-401–425) — DONE 2026-11-02
- SAM×3 (Wikimedia eval frames): frame1 no-box (honest), frame2 BOX with overlay+mask, frame3 no-box. VARIANCE.md: same frame box-once/no-box-under-other-prompt (matches Pax/OC1 variance). Patrol wiring run exercised with degraded branch.
- Wonder swap: case1 agree→confirmed, case3 emergency→confirmed/structure-fire/high, case2 transport flake→falls back to combine() (recorded, no retry). COMPARE.md: model agrees with deterministic combine 2/2 where it answered.
- Judge-v2 live: standalone run fell back (deterministic + named fallback); judge_mode:model PROVEN live in the patrol dry run (same wiring, model reasons quoted). Forced-failure (bad endpoint→401) fallback named. PASS.
- Image×2 (lab + workshop scenes, GENERATED filenames), magic-byte CHECKS.md PASS. Transcribe: all 3 surfaces 404 (was model_not_found at probe time — verdict uncallable stands, one-line update proposed, file not edited).
- Patrol dry run: Spark vision→vehicle fire/high, SAM no-box (honest gap), second Spark review, judge confirmed/model, loopback dispatch POST /fire receipt sim-oc2b-patrol-001. PASS.
- Spend ≈$0.06 attributable (§17), guardrail-wide $0.152/$75 (headroom $74.85). Receipts indexed. Key grep sweep: zero hits required → met (7 key-shaped hits all triaged as other lanes' hashes, none in §17 files).
- Truth: the pipeline cuts when it cuts and no-boxes honestly, for about six cents. Landed. Flake on record: metered-but-empty responses hit 2/8 calls — all callers must treat empty content as failure, never retry-loop.

## Section 18 — Live cameras on the Mac (OC2B-426–450) — DONE 2026-11-02
- List: 976 online cameras (Manhattan 377 / Queens 211 / Brooklyn 207 / SI 100 / Bronx 81). Egress: Mac GET 200, 251,050 bytes. No degraded path needed — all frames fresh Mac fetches.
- 5 borough snapshots (named cam-id frames) + direct by-id fetch. 6/6 readings OK (vigiles×3, ignis, medicus×2), zero UNPROVEN. Slowest: medicus/Manhattan 17,555 ms.
- Round-robin 5 distinct cameras; staleness: same camera 384 s apart, bytes changed (live, not stale); offline exclusion proven via injected isOnline:false entry. test_livecams: 12 OK. JPEG magic+PIL check PASS. Online-count delta: 976 live vs 1 committed proof capture (+975; committed dir is a single capture, not a census).
- Frames ≤35 KB each; nothing over 1 MB. Spend $0.04114 (6 assess calls). Exact commands in status per task (livecams.py --assess-one --area ...).
- Truth: the live path proved on the Mac with real frames and real readings. Landed. Nothing blocked.

## Section 19 — Musica runs + Goose gate-2 (OC2B-451–475) — DONE 2026-11-02
- Musica: pretty_midi 0.2.11.0 via pip3. Suite 39 pass / 0 fail (prior 37/2 missing-pretty_midi resolved; 2 re-runs PASS). 2 generation paths end-to-end (4 keepers, 4 .mid 178–279 B, all parse via pretty_midi). MAC-ONLY: none.
- Goose: binary `/Users/test/mcp-servers/toolchains/goose-src/build/goose` (b781587, provenance recorded). run-goose-tests.sh still hardcodes that path (grep count 1 — grepped only, never executed/edited).
- Gate-2 via `goose check` per file: 53 entries, 10 PASS (6 roots + echo/heartbeat/hello/mcp-host), 40 FAIL (one shared cause: per-file check resolves `import common.*` beside the file — every first-error verbatim for Buffy R12, nothing fixed), 3 SKIP (registry/devmgr/sockets READMEs). node --test with GOOSE=<mac binary>: 4/4 PASS. Path-fix diff sketch as text only.
- Wall time ~6 min. Artifacts ≤1 MB.
- Truth: music plays and parses; the goose runner's failure mode is mapped file-by-file for its owner. Landed. Nothing blocked (no fixes made — out of lane by design).

## Section 6 — Carrier image rebuild + verification (OC2B-126–150) — DONE 2026-11-02
- STATUS read: lane STATUS quoted + PARTIALs listed in `OC2B-img-status.md`. Rebuild via lane script `os-build/face/build-image.sh` (Linux debootstrap variant not usable on Mac — recorded, not run). Output `/tmp/oc2b-img-build/metaos-face.img`, 448,790,736 B, sha256 f7d8581e… (byte-identical to face lane's 06:47 build — reproducible YES). No failure (OC2B-144 no-failure line). Wall ~25s (cache-hit). No .img staged.
- Verified: boot log, desktop screendump (autologin relay, no typing), autologin YES ×2 (incl. 2nd-boot repeat), DHCP 10.0.2.15/24, egress 200, dashboard HTTP 200 local (host-forwarded check: forwarding not set up — blocker noted, not faked), boot times (1st ~178s cloud-init / steady-state 64s), idle mem 212/1967M, clock synced (36s→0s via timesyncd), shutdown 7s clean.
- node/git/chromium ABSENT from lane build output (verified, quoted lane reference not re-verified). Face-in-chromium BLOCKED at lane end (apt install running when lane closed) → carried UNPROVEN, remediation is §7 bake scope.
- Verdict table `OC2B-img-verdict.md` (PARTIAL→PROVEN/UNPROVEN). sha re-match confirmed. Gaps listed (bake-in §7, chromium/face). QEMU cmdline verbatim in `OC2B-img-section6.md`.
- Landed: reproducible image + 90% verification. In flight: face-in-chromium (needs §7 guest session). Blocked: host-forwarded dashboard check (no forwarding set up).

## Section 7 — Bake OpenCode + toolchain into image (OC2B-151–175) — DONE 2026-11-02
- Install: official script, `opencode --version` 1.19.5 — ONLY under `-cpu max` (default qemu64 CPU → Illegal instruction; rebooted with -cpu max, recorded). Smoke: endpoint UnknownError err_7c808c65, 41.7s, no reply (one attempt, no retry).
- MCP config shape only (redacted, stub path). LAYERS test blocked on same endpoint error (recorded, not retried).
- Bake: `/home/relay/bake/meta-os` depth-1 clone (28.9s, 246M) @ b0a66bf. git 2.39.5 installed. Updater service+timer installed+enabled (redacted, no secrets). Toolchain: opencode 1.19.5, git, curl, python3 (node/chromium out of scope — gap).
- Baked file `/tmp/metaos-2026-11-02-oc2b-baked.qcow2`, 1,587,019,776 B (+253.6% vs base), sha 849219f3… (pre-boot). Boot log kept. --version + checkout verified on 2nd boot (persistence YES). Manual pull ran clean, no move in-session.
- Desktop screendump IMPOSSIBLE (no desktop env in server image) — none claimed. Dashboard in baked image: 000 (no listener; §6 base-200 was lane server context — named). In-image model smoke: endpoint error, no client receipt. Clock/sizes/gaps/filename recorded in `OC2B-oc-verify.md`.
- Landed: baked, bootable, versioned image with updater. In flight: none. Blocked: model endpoint (server-side), desktop/chromium (needs GUI base image), dashboard server in image.
