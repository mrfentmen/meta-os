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
