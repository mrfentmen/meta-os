# Bond — Wave 3: programs only (no QEMU, per Del's ruling 2026-11-02)

**From:** Pax. **Branch:** `bond/wave3`, off current main. Commit per section. Never push main.
**Status file:** `os-build/BOND_WAVE3_STATUS.md` — same honesty labels as wave 2.
**Lane:** programs, tests, records, audits. No QEMU, no boot gates, no kernel source — boot
proofs belong to OpenCode 1, OpenCode 2 and Buffy. The light gate is your ceiling by design.

## Section 1 — Science reproduction (unblocked: the lab is merged)

1. Re-run OpenCode 2's dress-rehearsal cycle from its committed records in a fresh directory:
   same held-out rows, same preregistered threshold. Verdict agree/disagree with the numbers.
2. Blind rule: do not read the rehearsal's result file until your run is written down.
3. Re-run the Hortus breeding example from its records; check the lineage chain verifies.
4. Re-run the Science Lab full suite on current main; record the count next to OC2's 163.
5. If any number disagrees, the disagreement record leads the status file — no silent fixes.

## Section 2 — Program proof ledger, round 2

6. Every row of the wave-2 ledger re-run at the new main tip: queue suite (now incl. the
   model + judge tests), products/schema, Hortus, Officina, agent runtime, watchman,
   baton+bridge, gym, board, relay, federation, ui-fix audit.
7. Science Lab added as a ledger row (suite + rehearsal + gateway records).
8. Aegis added as a row: modules load + the hosted runner's exit, labelled host-side.
9. Each row: command, count, evidence path. A row you did not run says so.

## Section 3 — Musica close-out

10. If `pretty_midi` is installed on your Mac by then: re-run the Musica suite; target is
    the 2 dependency failures gone and any real failure named. If it is still missing,
    record BLOCKED-missing-dep once and move on — do not re-run the failing pair daily.

## Section 4 — Goose services, paper lane

11. Write up the runner defect precisely: `services/run-goose-tests.sh` hardcodes
    `/Users/test/mcp-servers/toolchains/goose-src/build/goose`. What the path should be
    (repo-relative or env), filed as a fix proposal — Buffy's services lane applies it.
12. Per-service contract records for the services the runner covers: stated contract vs
    code, gaps as records. No binary runs claimed — the binary is absent on your machine.

## Section 5 — Model receipts verification

13. Parse every committed model receipt artifact (wave-2 §3 era + any newer): schema check
    (model id, timestamp, mode), ids against the served list, judge_mode records present.
14. Spend lines: every dollar figure in the receipts is an estimate at Spark rates unless
    the receipt says otherwise — flag any that reads as exact.

## Section 6 — Kernel reading, round 2 (read-only)

15. Correct the wave-2 §7 record: readkey against the combined tree + the WAVE3 proof log
    (it runs; the earlier "not started by main.rs" note gets its precise correction).
16. Updated kernel census at the new tip (line counts, files) next to the wave-2 numbers.

## Section 7 — Face, full click-through

17. Serve the face locally and click EVERY dock entry this time — wave 2 verified Science
    and inspected the rest. One screenshot + verdict per app: opens, renders, honest state.
18. The :18934 lesson applied: for each system window, record what must be serving for it
    to render, and what the user sees when nothing is serving.

## Section 8 — README audit, round 2

19. When Pax's expanded README lands (today), audit it line by line against the tree:
    every program named exists, every count matches a run, Custos retired everywhere.
20. File the audit as `os-build/README_AUDIT_BOND_W3.md`; disagreements listed, not fixed
    by you — Pax owns the README text.

## Closeout

21. Status file complete with the wave-2 labels; anything BLOCKED names its blocker and
    its owner. No boot claim, no model-call claim, anywhere in the wave.
