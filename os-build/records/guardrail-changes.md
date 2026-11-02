# crates/guardrail — changelog record (B168)

Port history from the committed records in this tree. This slice had no
git terminal, so **no commit hashes or dates are invented**; the source
for each entry is named. To append the exact trail, run:

```bash
git log --oneline --follow -- crates/guardrail
```

## Entries

| When (source) | Change | Evidence |
|---|---|---|
| B00 skeleton | Workspace member `crates/guardrail` created with the batch header; no logic | `Cargo.toml` + crate header (`src/lib.rs:1-10`), `BATCHES.md:82-86` |
| B03 | Guardrail + Spark transport ported from `spark_guardrail.py` and `spark_gen.py`: constants, `GuardrailState`/`UsageLog`, `load_state`/`save_state`, `check`, `estimate`, `record`, `status_of`, `unwrap_model_text`, `build_prompt`, `via_helper`, five unit tests | `src/lib.rs` as it stands; batch map `TASKS.md:138-140` |
| T246 dedup pass | `assess-server` delegates its pre-send check and post-response record to this crate instead of keeping a second copy: `guardrail::check` + `guardrail::record` at `main.rs:436,471` | `OPENCODE_FINISH_REPORT.md:69-72` |
| B11 routing plan | Assess-server routes Spark counting through B03's guardrail, never a second counter | `docs/RUST_REBUILD_PLAN.md:266` |
| This pass (2026-11-02) | Doc-only corrections: `load_state` now states that every read/parse failure returns zero; `record` now states the fixed timestamp and ignored write failure; `build_prompt` now states the four prompt paragraphs it does **not** carry. No behaviour changed | `src/lib.rs:54-56,84-85,134-138` (comments) |

## What did not change in this pass

- No constants, no struct fields, no function signatures, no refusal
  text, no file format.
- The five original unit tests are untouched.
- No dependency was added or removed.

## Test history visible in this tree

| Tests | Where | What they pin |
|---|---|---|
| 5 unit | `src/lib.rs:166-203` | estimate maths, record count/cumulative, stop at budget, pass under budget, fence unwrap |
| 38 integration (new) | `tests/error_paths.rs` (19), `tests/edge_cases.rs` (10), `tests/gap_close.rs` (9) | refusals, swallow points, empty/max/duplicate/out-of-order, status shape, constants, round-trip |

The count is lines in the files, not an estimate: `grep -c '^#\[test\]'`
over the three files returns 19 + 10 + 9.

## Commit history (appended by coordinator, from git)

- 5d7ec68 2026-10-30 B07: wave-1 integration (B02-B05 ports over main B01+B06) + parity-tests E0119 seam fix — UNCOMPILED (gate 2 pending)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
