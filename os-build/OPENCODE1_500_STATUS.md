# OPENCODE1 500 STATUS — opencode/500 (started 2026-11-02 ~11:00 EST)

Rules: commit per section, proof lines per task, UNPROVEN named. Wave-2 soak verdict: RUNNING (/tmp/soak3-serial.txt, 20 samples, 0 panics, ends ~11:25 EST).

## §8 Combined-tree re-proofs (OC1B-176..200) — MERGED 2026-11-02
Branch opencode/500-s8 @ 0efdde56. Verdict: NO REGRESSION. Five wave slots NO WAVE (no kernel-touching merge c7aeb162..94010c76); combined tip re-proven: gate GREEN 8/8, serial 1086 lines panic 0, queue-python 296 OK, crew-wiring 7 OK. Deltas: readkey got=13 vs got=3 (input-length method diff), readkey ELF +8 bytes same behavior. Full block: os-build/logs/OC1B-s8-STATUS-SNIPPET.md.

## §17/§19/§20 (OC1B-401..425, 451..500) — MERGED 2026-11-02
Branch opencode/500-s17 @ f4e506f8 (commits 9283798d/e1512446/f4e506f8). §17 DONE: native suite 2071 run/2015 pass/56 fail (3.4s); settled 56 = 31 whole-file + 24 named + 1 newcomer R11-282 (boot-log index drift, fails on main too); groups G1-G7+SUPP sum closes; UPDATE 38 / CARVE-OUT 17 costed in os-build/NATIVE_55_DECISION_PACK.md; no test/source edits; closeout gate.sh GREEN on same tree. §19 PARTIAL: prep committed (walk/attributions/secrets-scan clean/snapshot/fields dry-run/timeline) but rehearsal BLOCKED (runbook missing: 463/465), 452 freshness + 453 receipts open, X draft missing, rows 1-2 need owners. §20 done-by-lane: closeout records committed; rows 420/424/469/493/497/500 coordinator-owned (497 not-done-by-fence); §20 kernel claims rest on §1/§8 lineage. Deviation (honest): OC1B-484's "empty syscalls history" fails — pre-existing Pax-merged Rowan draft 4bf2367f touches the path, quoted in lane proof, lane adds nothing. Full blocks: os-build/logs/OC1B-s17-STATUS-SNIPPET.md.
