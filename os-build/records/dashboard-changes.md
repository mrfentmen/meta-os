# `dashboard` — changelog (B156)

Status: **CODE-INSPECTED**, not git-derived. This worker had no
terminal, so it could not read `git log`. The timeline below comes from
the checked-in batch records (`batches/B15.md`, `BATCHES.md:419-431`)
and the crate headers. Commit hashes and dates are deliberately not
invented; the command to append them is at the bottom.

## Timeline

### B00 — skeleton

- `crates/dashboard` joined the workspace (`Cargo.toml:10`).
- The crate existed as a placeholder; `src/lib.rs` described itself as
  "skeleton (B00)" with "no logic yet". That header survived into a
  tree where it was no longer true (corrected this pass).

### B15 — Dashboard backend contract (owner: Hana)

Source records: `batches/B15.md`, `BATCHES.md:419-431`,
`SUPER_PROMPT.md:409-418` (T236-T243).

- `src/contract.rs` added: brief payload/staleness, palette contrast
  math, verdicts, Brief section order/titles, alerts feed, deep links,
  demo mode, today counters, error rows, posting gates, rollback pins,
  crew-board §7 rules, keyless signing entry builders, alert lifecycle.
- Five fixture documents carried under `crates/dashboard/fixtures/`:
  `DASHBOARD_SPEC.md`, `DASHBOARD_SMOKE_CHECKLIST.md`,
  `DSH-035-CROSS-BROWSER-CHECK.md`, `DEPLOY_RUNBOOK.md`, `DEMO.md`.
- Four parity test files added: `b15_parity.rs`, `b15_crewboard.rs`,
  `b15_spec_notes.rs`, `b15_rollback_parity.rs`.
- Viewer-dependent cases were recorded exclusion-blocked, never faked
  green (`tests/b15_parity.rs:1-60`).
- The crate header still said "skeleton (B00)"; the batch record says
  PORTED subject to gates.

### 2026-11-02 — BOND lane pass (this change set)

Changed:

- `src/lib.rs:1` — header corrected from "skeleton (B00)" / "no logic
  yet" to the B15 backend contract. No code changed.
- `tests/error_paths.rs` (new) — every refusal message, the short-hex
  panic, and the silent zero-channel path.
- `tests/edge_cases.rs` (new) — empty / maximum / duplicate /
  out-of-order inputs and the stale, midnight and zero-budget
  boundaries.
- `tests/gap_close.rs` (new) — constants and helpers no existing file
  exercised directly (verdict list, brief kinds, rollback steps,
  `resolve_brief_link`, `default_open`, stale humanisation,
  `addressable_cards`, `route_encode_id`, `py_str_json`, nonce shape,
  lifecycle fallback, counts).
- Records added under `os-build/records/`: `dashboard.md`,
  `dashboard-gaps.md`, `dashboard-records.md`, `dashboard-callers.md`,
  `dashboard-config.md`, `dashboard-drill.md`, `dashboard-surface.md`,
  `dashboard-changes.md` (this file).

Unchanged:

- `src/contract.rs` logic and all existing tests. `Cargo.toml`,
  fixtures and package metadata untouched.
- No production behaviour changed; no API widened.

## Findings carried forward (not fixed here)

The seven findings in `dashboard.md` section 15, including the WCAG
panic, the unreachable `human_age` branch, the `VERDICTS` dead
constant, and the numeric-only `resolve_brief_link`.

## How to replace the guessed timeline with real history

```sh
git log --oneline --decorate -- crates/dashboard
git log --stat -- crates/dashboard/src crates/dashboard/tests
```

Append the commits above B00/B15 and this pass. Until then, the
timeline is the batch-record version, not a commit list.

## Commit history (appended by coordinator, from git)

- afeb473 2026-11-01 No-mocks purge of old references (boss order 2026-11-01): dashboard mock approval shape removed, panel is read-only with no approve action, posting CLI only; plan/spec/report/comment mock references purged; facts and safety rules preserved
- 584ea74 2026-11-01 No-mocks purge of old references (boss order 2026-11-01): dashboard mock approval shape removed, panel is read-only with no approve action, posting CLI only; plan/spec/report/comment mock references purged; facts and safety rules preserved
- 78915ed 2026-10-30 B15: crate docs for dashboard contract (T245) — UNCOMPILED
- e1ed8b8 2026-10-30 B15: today counters record rules (DSH-032) — UNCOMPILED
- 4399ca8 2026-10-30 B15: brief sections default-open map + titles/order (DSH-031) — UNCOMPILED
- 78e3469 2026-10-30 B15: alert lifecycle resolved-collapse count — UNCOMPILED
- e864102 2026-10-30 B15: alert lifecycle resolve end-state rows — UNCOMPILED
- 0c78093 2026-10-30 B15: alert lifecycle WDG-014 rule half — UNCOMPILED
- ed93561 2026-10-30 B15: crewboard §7 rules + signing builders (T237) — UNCOMPILED
- 5bd9ba2 2026-10-30 B15: spec-note parity (T238/T239/T240/T241/T242 partials) — UNCOMPILED
- c65317e 2026-10-30 B15: accessibility contrast parity (T238 partial) — UNCOMPILED
- 33f5179 2026-10-30 B15: smoke checklist structure parity (T242 partial) — UNCOMPILED
- b59193f 2026-10-30 B15: rollback INT-031 remaining pins (T241) — UNCOMPILED
- 17bb62a 2026-10-30 B15: deploy runbook parity — UNCOMPILED
- 45600e0 2026-10-30 B15: dashboard crate docs — UNCOMPILED
- d925caf 2026-10-30 B15: dashboard backend contract — UNCOMPILED
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
