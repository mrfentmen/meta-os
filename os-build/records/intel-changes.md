# `crates/intel` — changelog record (B180)

## Method note — what this record can and cannot say

This pass had no terminal, so **`git log` was not readable**. Nothing
below invents a commit hash, a date, or an author. Each entry is taken
from a file that is committed in the tree: the crate header, the
subtree module maps, the batch docs, and the test files.

To append the real history:

```sh
git log --oneline --decorate -- crates/intel
git log --stat -- crates/intel/src crates/intel/tests
```

The record below is the state of the port as the tree describes it,
not a commit-by-commit timeline. When the git trail is added, it goes
under "Commit trail" at the end; it does not replace these entries.

## Port batches

| Batch | Subtree | Source files it ports | State in this tree |
|---|---|---|---|
| B09 | `b09_core` (`lib.rs:71-110`) | `os/intel.py`, `os/intel/__init__.py`, `capability.py`, `capability_files.py`, `explanations.py`, `gate.py`, `ingest.py`, `integration.py`, `join.py`, `ladder.py`, `store.py` | 11 modules present; parity file `tests/b09_parity.rs` covers capability, capability_files, explanations, gate, join, ladder, store, plus inline cli/ingest/integration. Fixtures carried under `fixtures/b09/` (five grants + README). |
| B10 | `b10_brief` (`lib.rs:76-90`, `b10_brief/mod.rs`) | `alerts.py`, `baton.py`, `brief.py` (+ `sections`, `window`), `dispatch.py`, `forecast.py`, `notify.py`, `push.py`, `wake.py` | 10 modules present; `tests/b10_parity.rs` covers alerts, baton, brief, dispatch, forecast, notify, push, sections, wake, window. Prompt fixtures under `fixtures/b10/prompts/` (8 prompts + README). |
| B11 | `b11_spark` | `mind_image.py`, `mind_loader.py`, `skills_loader.py`, `spark_agent.py`, `spark_client.py` | 5 modules present; `tests/b11_parity.rs` covers the unconfigured/error paths, both transports, the stub, and mind-image/loader shapes. |
| B12a | `b12a_drills` | 39 code files: top-level checks (`abrun`, `boot_audio_check`, `boot_selfcheck`, `dem018_local_check`, `e2e1..3`, `final_mix_check`, `load_check`, `redis_down_drill`, `sam_check`, `sam_render`, `security_pass`, `soak_review`, `spark_down_drill`, `spoof_dispatch_drill`, `watchdog_tuning`, `evals/watchdog_tuning`) plus `drills/` (21 drill modules) | Modules present; `tests/b12a_parity.rs` covers boot_selfcheck, sam_check, security_pass, soak_review, watchdog_tuning and `drills::demo_thresholds_dropin`. Cross-batch surfaces are traits in `deps.rs`, not adapters. |
| B13 | `b13_devpack` | `os/intel/devpack.py` (DSH-037) | Shapers present; `tests/b13_parity.rs` re-derives every payload from real producers and compares with the checked-in pack. Fixtures under `fixtures/b13/` (22 files). |
| B14 | `b14_trust` | `trust.py`, `timer_sweep.py`, `launch_run.py`, `metaos-demo.env` | 3 modules + demo fixture; `tests/b14_parity.rs` covers unsigned/negative refusal, tick dedupe, expired-claim sweep, launch verify-first, and the demo profile. |

## What changed in this pass (B175-B180)

Read-only records and one test file; **no `src/` change**.

| File | Change |
|---|---|
| `os-build/records/intel-callers.md` | New. Every caller, the trait seams that are not adapters, and the Python live path. |
| `os-build/records/intel-config.md` | New. Env vars, files, injected config, refusals. |
| `os-build/records/intel-drill.md` | New. Failure order plus four runnable drills. |
| `os-build/records/intel-surface.md` | New. Public names per module with usage class. |
| `os-build/records/intel-changes.md` | This file. |
| `crates/intel/tests/gap_close.rs` | New. Nine cases for `b09_core::ingest`, the thinnest-tested module (1 test), bringing it to the depth of the best-covered module (`brief`, 10). |

## Tree evidence at this pass

- Crate source: 6 subtrees, `lib.rs` module map; 148 in-file `#[test]`
  functions across `src/` (count from source, not a test run).
- Integration tests: 6 files under `crates/intel/tests/` (`b09`, `b10`,
  `b11`, `b12a`, `b13`, `b14` parity).
- Fixtures: `fixtures/b09/` (grants), `fixtures/b10/prompts/`,
  `fixtures/b13/` (pack), `fixtures/b14/` (demo env), plus
  `fixtures/evals/` records.
- Dependencies: none (`crates/intel/Cargo.toml` has no `[dependencies]`).

## Known drift recorded elsewhere, not fixed here

- The crate is not wired into any other crate; no binary, no adapter.
- B12a drills call traits; the real B09/B10/B21 implementations are not
  adapted yet (`intel-callers.md`).
- `MUSE_RELAY_KEY_PREFIX` is re-read per key call, unlike the Python's
  import-time constant (`intel-config.md`, finding 1).
- `trust::recompute_sig` is a toy FNV stand-in, explicitly labelled as
  needing real HMAC before PORTED (`trust.rs:48-50`).

## Commit history (appended by coordinator, from git)

- dd7c683 2026-11-01 No-mocks purge of old references (boss order 2026-11-01): dashboard mock approval shape removed, panel is read-only with no approve action, posting CLI only; plan/spec/report/comment mock references purged; facts and safety rules preserved
- d0b6af7 2026-11-01 No-mocks purge of old references (boss order 2026-11-01): dashboard mock approval shape removed, panel is read-only with no approve action, posting CLI only; plan/spec/report/comment mock references purged; facts and safety rules preserved
- a566a38 2026-11-01 No-mocks purge of old references (boss order 2026-11-01): dashboard mock approval shape removed, panel is read-only with no approve action, posting CLI only; plan/spec/report/comment mock references purged; facts and safety rules preserved
- f17b8ff 2026-10-30 Mac gate2: merge batch/B10 intel union (gate-1 108 passed)
- 34c1991 2026-10-30 B10: intel union — b09_core subtree + crate root (T190 unblock) — UNCOMPILED
- dc1efcd 2026-10-30 B10: source pointer lines (T190 partial) — UNCOMPILED
- 12d137b 2026-10-30 B10: recovery line OS-127 (T190 partial) — UNCOMPILED
- 16065b2 2026-10-30 B10: previous-session digest + system-state lines (T190 partial) — UNCOMPILED
- 43f199d 2026-10-30 B10: brief prompt path + load (T190 partial) — UNCOMPILED
- c5715bf 2026-10-30 B10: brief constants + canned failure lines + trim-to-budget (T190 partial) — UNCOMPILED
- 1142491 2026-10-30 B10: brief window line + message parts (T190 partial) — UNCOMPILED
- 357402d 2026-10-30 B10: brief section derivation (T190 partial) — UNCOMPILED
- a0f626f 2026-10-30 FINISH: merge batch/B12a - intel union +b12a_drills (local gate, recheck pending)
- 1e4f635 2026-10-30 FINISH: merge batch/B12c - eval fixtures P-W+SAM CARRIED
- 3a9abb4 2026-10-30 FINISH: merge batch/B12b - eval fixtures A-L CARRIED
- 1d1d745 2026-10-30 FINISH: merge batch/B14 - intel union +b14_trust
- 694899a 2026-10-30 FINISH: merge batch/B13 - intel union +b13_devpack
- 75d39b0 2026-10-30 FINISH: merge batch/B11 - intel union b09+b10+b11
- dd98b20 2026-10-30 FINISH: merge batch/B10 - intel union b09+b10
- 34a37c4 2026-10-30 T216 [B12a] fix 6 gate-1 compile errors (E0618/E0599/E0631/E0277/E0716 x2) - UNCOMPILED, gate-1 recheck pending
- 9f2a24b 2026-10-30 B12a: parity test rewritten — UNCOMPILED (Pax)
- f3f449c 2026-10-30 B12a: drills trust_negative + wake — UNCOMPILED (Pax)
- 919f958 2026-10-30 B12a: drills ladder/soak/timer/tournament/trust — UNCOMPILED (Pax)
- 3473f63 2026-10-30 B12a: drills demo/keys + spoof dispatch — UNCOMPILED (Pax)
- a70a07e 2026-10-30 B12a: T212 drills/boot_status, capability_refusal, collision, dead_dep, demo_catch_time ported — UNCOMPILED (Pax)

