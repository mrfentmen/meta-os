# B07 — Wave 1 integration report

- **Run by:** Rowan, 2026-10-30 (~08:50 EDT), on this VM (cargo/rustc 1.99.1).
- **Vehicle:** branch `batch/B07`, stacked on the B07 gate commit `a2edd44`
  (base = main `b2411c4`, tree identical). Nothing merged to main. Note:
  `a2edd44` recorded the Mac gate as BLOCKED on the parity-tests E0119 —
  that exact error is fixed by the seam fix in this commit (item 2 below).
- **Contents:** the B02–B05 ports integrated over main's B01 + B06 —
  queue-store (from `batch/B02` 1d8bf1e), guardrail (`batch/B03` df3fef3),
  agent-runtime (`batch/B04` 45a4833), assess-server (`batch/B05` 5ea9995) —
  plus one seam fix (below), the regenerated `Cargo.lock`, and this report.
- **Why:** Milo's gate 1 is finished (boss's word); this branch is the gate-2
  vehicle. On the Mac: pull `batch/B07`, then `cargo build --workspace` and
  `cargo test --workspace`.

## Checklist

1. **Workspace build — PASS.** `cargo build --workspace` clean after the seam
   fix. Before it, the only failure in the whole workspace was parity-tests
   E0119 (below).
2. **Seam fix (owning crate, one line):** parity-tests — `FakeUpstash` had
   both `#[derive(Default)]` and a manual `impl Default` (which just calls
   `Self::new()`). Removed `Default` from the derive at
   `crates/parity-tests/src/support/fake_redis.rs:15`. Committed here as a
   B07 seam fix, UNCOMPILED pending gates; the B31 line's own fix may
   supersede it there.
3. **Contract seam check — PASS** on every frozen point:
   - job kind `trio-assessment`, envelope version 1 (queue-core);
   - job id `trio-` + first 32 hex of sha256(product + "\0" + timestamp +
     "\0" + frame bytes) (queue-core);
   - result key `trio:{jid}:result` (queue-store);
   - result body `{job_id, status, assessment, error, model, latency_ms,
     completed_at}` (queue-store);
   - queue claim = SET NX with lease expiry + XX heartbeat semantics
     (queue-store);
   - guardrail counts every Spark call against the $75 test cap and refuses
     at the cap (guardrail, `TEST_BUDGET_USD = 75.0`, stop-at-budget test);
   - `/api/assess` v2 request validation present (assess-server
     `validate_assess_request`).
4. **Cross-crate test pass — wave 1 green; one external abort, triaged.**
   - The six wave-1 crates together: **39/39 pass** (queue-core 12,
     queue-store 5, guardrail 5, agent-runtime 2, assess-server 2, stack 13).
   - Whole workspace excluding parity-tests: **86/86 pass, 0 fail**.
   - parity-tests lib run **aborts**: `support::fake_redis::tests::
     lrem_semantics` overflows its stack (infinite recursion in the fake's
     lrem path). One test (`empty_and_bad`) passed before the abort; the
     process died, so the rest never reported. **Triaged to B31** (owning
     batch) — B07 files the seam, it does not rewrite another batch's port.
     Expect this same abort on the Mac run until B31 lands its fix.
5. **Compile-error triage (wave classes):** E0119 duplicate definition —
   fixed here (seam, above). E0433 os-misc dev-dependency — seen at gate 1
   on B31 branch tips; **not** present in this tree's parity-tests.
   Runtime stack overflow (fake_redis lrem) — B31, filed above. Stall rule
   noted: the parity-tests compile class has recurred across gate-1
   rounds; it stays parked with B31.
6. **Fallback integrity — PASS.** This branch changes only `crates/**`,
   `Cargo.lock`, and this report relative to main `b2411c4`. No Python,
   Node, or Swift original was edited or deleted. Node suite on the
   integrated tree: **1906/1906, 0 failures**.

## Parity notes (filed 2026-10-30 ~06:35 EDT, unchanged by this run)

- B05 assess-server: `main()` only prints — no HTTP serve loop, no
  queue-first poll, no 502 path yet. Helpers match the frozen shapes; it
  cannot serve yet. Owner: B05.
- B04 agent-runtime: `validate_stub` is a category-only stand-in for the
  Node `validateAssessment`; ok-gating is weaker than the frozen contract
  until the real gate lands. Owner: B04.
- B03 guardrail: `record()` UsageLog timestamp hardcoded
  `2026-10-30T00:00:00Z` vs Python `datetime.now`. Nit, owner: B03.

## Status

`B07 BLOCKED wave=1 workspace-build=pass workspace-test=86/86 excl. parity-tests (lib aborts: lrem_semantics stack overflow, B31) — wave-1 crates 39/39 — gate 2 (Mac) pending`
