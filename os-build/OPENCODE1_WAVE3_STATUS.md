# OPENCODE1 WAVE3 STATUS — opencode/wave3 (started from current main 2026-11-02)

Rules: commit per section, proof lines per task, UNPROVEN named never hidden.
Lane exclusions hold (no kernel/src, no registry.json, no science-lab/**, no labs/**).
Wave-2 soak: soak3 running on wave2-tree image (verdict at end; wave-2 §19).
Image parts: removed from git per repo rule (face commit c75811ef); local copies kept.

## Section 1 — combined kernel tree (1-10): DONE 2026-11-02
Clean clone 6524ebaf, gate GREEN, VNC boot: banner/alive/0 panic, userspace set, readkey typed bytes (got=3), fetch screen, status ticks moved, mem/ps 8 rows, bad syscall refused. Proof: WAVE3_KERNEL_PROOF.md + serial + 3 shots.

## Section 2 — soak + stability (11-16): OPEN (soak3 running on wave2 image; fresh soak on sec-1 image pending)
## Section 3 — model pipeline, live (17-28): DONE 2026-11-02
Queue 141/141 pre-live. Wonder chat OK, SAM 2x no-box (recorded), Spark reading live, image generated (webp 60KB). Judge-model incident: judge_mode deterministic (Spark empty reply x3, direct prompt works) — model side UNPROVEN, fallback PROVEN. Spend $0.016. Proof: WAVE3_MODEL_PROOFS.md + artifacts.

## Section 4 — demo final form (29-37): DONE 2026-11-02
Beat 6 rebuilt with judge step (receipt sim-8040104f5e0c7d23 filed run, deterministic+fallback named). Film 180.000s exact, t=10/t=160 verified. Runbook written + rehearsed (branch gate GREEN b85Q5D); 4 rehearsal gaps found and fixed/recorded. Proof: os-build/demo/ (mp4, frames, CAPTURE_NOTES, DEMO_RUNBOOK).
## Section 3 — model pipeline, live (17-28): DONE with one UNPROVEN 2026-11-02
Queue 277/277 pre-live. Wonder chat OK, SAM 2x no-box (recorded), Spark reading live (structure fire), image generated (webp 43KB). Judge incident: deterministic + named fallback (model empty-reply, direct prompt works) — model-mode UNPROVEN with reason. Spend $0.0216. Proof: WAVE3_MODEL_PROOFS.md + wave3-model-proofs/.
## Section 5 — carrier image toolchain (39-48): BLOCKED with cause 2026-11-02
Read recipe + sec4 notes. Attempted per recipe on the live guest: apt npm OK; opencode postinstall FAILS (needs linux-x64-baseline pkg, installed); baseline binary + freebuff 0.2.27 install clean BUT both die at exec with SIGILL (Illegal instruction, exit 132) — QEMU Virtual CPU 2.5+ lacks instructions even baseline builds need. NOT baked (a crashing binary is worse than absent). Rebuild skipped: base recipe unchanged, bake would not fix a CPU wall. 4 standing checks re-verified live (facts/rooms/trash 200, updater pulls). Kiosk starts (guest-desktop shots). opencode --version: UNPROVEN (SIGILL verbatim above, not a silent skip).
## Section 6 — Imperium gaps (49-58): DONE with named gaps 2026-11-02
Cleared+purge PROVEN, inconclusive PROVEN, BOLO shown on dispatch path. Budget/STOP-file/supervisor: no mechanism on tree (recorded, not faked). Goose: no Mac runner. Ledger 4/4 lack brief/outcome/receipt (finding). Proof: WAVE3_IMPERIUM_GAPS.md + wave3-imperium-gaps/.
## Section 7 — native-55 decision pack (59-66): DONE 2026-11-02 (analysis only, zero changes)
1965/55 reproduced; 31 size files + 25 parity names grouped; update touches ~36 files, carve-out ~6 files losing drift coverage. Pack: os-build/NATIVE_55_DECISION_PACK.md. One-line: the 55 are all native-mirror drift, update-or-carve is Del's call.
## Section 8 — README + submission (67-76): DONE (drafts only) 2026-11-02
README node counts fixed (one commit); Rust badge left stale deliberately (red, nothing to claim). Forms dry-run with DEL-ONLY fields; FREEZE_CERT drafted from proven claims; X draft written (Del posts); film paths on branch-not-main flagged; DEL-ONLY list recorded. Proof: WAVE3_SUBMISSION_PREP.md.
## Section 2 — soak + stability (11-16): RUNNING 2026-11-02
Wave-2 soak (soak3, wave2 image): 10 start samples, 0 panics, still in window. Fresh soak on Section-1 image RUNNING (soak-w3). Pack drill 10/10 green (hello/exit0 x3/fault/sleepback/readkey each run, 0 panics): WAVE3-pack-drill.log. Verdict + WAVE3_SOAK.md at soak end.