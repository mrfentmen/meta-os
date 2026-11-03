# PROOF-e5ce311b.md — post-merge proof duty (MORE_TASKS #3)

Tip: `e5ce311b` (merge batch on main). Worktree: detached /tmp/merge-tip3.
Exact commands (all from the worktree root):

1. `sh os-build/gate.sh` → GATE GREEN 7/7.
   Log: /tmp/merge-tip3-gate.log. Boot: /tmp/gate-boot-CENl03
   (K1 alive, K4 mem summary, K6 ring-3 hello, clean exit, fault
   isolation, shell answered, STATUS live, 0 loader-refused).
2. Cargo workspace check: `cargo check --workspace` (nightly
   1.101.0, PATH pinned via rustup nightly rustc) → FINISHED,
   warnings only (unused imports/deps), zero errors.
   Log: /tmp/proof-cargo-check.log.
   (Note: full `cargo test --workspace` on the sibling prove-main
   tree REDs on os-supervisor test-target E0271 x2 — test-code
   closure issue, supervisor lane; check itself is green here.)
3. Node suite: `npm test` → 1951 pass, 55 fail (runner ℹ lines).
   Log: /tmp/proof-node.log. The 55 fail the same native-parity
   set as the ab763ac0 run (31 tests/native-* files + 6
   ui.test.mjs parity subtests tracking native-side changes);
   4 more passes than that run (1947 -> 1951), fail count steady.
4. Queue python suite:
   `TRIO_STORE=local TRIO_LOCAL_DB=/tmp/proof-crew.db
   TRIO_JOB_NS=proof python3 -m unittest discover -s tests/queue-python`
   → Ran 128 tests, OK. Log: inline (3.7s).
   No Spark keys, no live calls (scripted assessors).

No RED in this batch's four checks. No source edits made for
this proof (worktree discarded after).
