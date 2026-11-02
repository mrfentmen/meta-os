# MILO — OS BUILD-OUT (boss order 2026-11-02 02:22 EST)

Your lanes: gates, records, the agent runtime (L5), claims.
Nothing merges kernel-side without your gate + a boot log.
Freeze 05:12; ML4-4 claim audit stays due 20:12 EST today.
Each task: done = artifact + one line to room 1.

## A. Gates and records (tonight)
A1 K-all.txt milestone line K3 → K6 (OpenCode flag; your file).
A2 Gate-1 verdict on every main tip until freeze, posted.
A3 FREEZE_CERT.md drafted now, filled at 05:12 (tip, gate,
   claim clause → log, or UNPROVEN).
A4 Scoreboard v6: fold in R5/R6 results (soak, Ignis loop,
   clean-clone gates) with sources.
A5 Gate script: one command that re-runs gate-1 checks on a tip
   and prints the verdict block for room 1.
A6 Branch watch: list every crew branch vs main at freeze;
   landed / stale / abandoned, one line each.
A7 Post-freeze gate rota: who gates what while the boss sleeps.

## B. Claim audit (ML4-4, due 20:12 EST)
B1 Claim sentence split into clauses; one audit row each.
B2 Boot clause → named logs. B3 Ring-3 clause → named logs.
B4 Three-programs clause → named logs. B5 Isolation clause →
   named logs. B6 Shell-state clause → named logs.
B7 One-command reproduction: run it yourself from a clean clone;
   record time, output, verdict.
B8 Imperium claims: dispatch package fields vs the R5-4 record.
B9 Picture claim: package picture fields vs endpoint receipt.
B10 Simulated labels: grep the tree; every simulated surface
   labelled, list any miss.
B11 Site claims vs repo facts (with Hana's E-pass as input).
B12 README claims vs repo facts. B13 Demo script claims (Hana
   A1) vs logs. B14 Numbers audit: every count in DEMO_FACTS
   re-measured or struck. B15 Publish the audit as
   os-build/CLAIM_AUDIT.md with verdicts, no soft language.

## C. Agent runtime — L5 (design + spec + tests)
C1 Agent process model v1 doc: what an agent is on Meta OS
   (task? service? Lobster host?) — options + recommendation.
C2 Spawn model: who may start an agent, with what limits.
C3 Kill model: who may stop one; what the agent sees first.
C4 Message model between agents (bus-shaped; rooms; ordering).
C5 Memory model: what an agent may persist, where, how much.
C6 Budget model: calls/time caps per agent (mirror the queue's).
C7 Permission model: filesystem, network, dispatch — default deny.
C8 Failure model: agent crash isolation proof obligations.
C9 Lobster binding review vs Buffy's LOBSTER_BINDING.md: gaps.
C10 Spec the five syscalls an agent host needs beyond F1 table.
C11-C20: one test-obligation spec per C1–C10 (what proof would
   close it, on which layer, run by whom).
C21 Agent registry format (name, lane, caps, owner) — draft.
C22 Crew-as-agents mapping: Rowan/Hana/Buffy/Pax entries drafted.

## D. Services gate duty (Buffy's corpus)
D1 Gate each BF6 slice as it lands (verdicts to room 1).
D2 Spot-check 5 services' drivers against their LIMITS claims.
D3 Goose gate-2 attempt (M-FP4 carries): run or name the blocker.
D4 Corpus count re-measure at freeze: files, lines, services,
   RUNS vs typecheck-only — one table, sourced.
D5 SERVICES_FINAL vs tree diff: any claim the tree contradicts.

## E. Eval and dataset records
E1 Eval ledger consolidation: batch 1 + 2 + R5-4 + R6-3 in one
   table (frames, verdicts, cost) — sourced from the records.
E2 Dataset inventory vs disk: the five pulls, sizes, licences.
E3 Spend ledger: API spend to date from the records; cap status.
E4 Sample-only rule compliance note for any future batch-3.
E5 "We claim our own data" — the sources page, updated.

## F. Watch duty
F1 Bus watch rota note: who polls when; stale-counter procedure
   (reset seen, then poll) written down once.
F2 Hourly status template: tip, gates, lanes, blockers, next.
F3 Escalation list: what wakes the boss (money, Mac results,
   his open decisions) vs what waits.
