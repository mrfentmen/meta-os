# crates/ ↔ host parity map (Lane D, 2026-11-04, R5)

Status word per pair uses the `os-build/LAYERS.md` vocabulary, scoped to the
pair (not the layer): VERIFIED = Lane D ran a live behavioral comparison this
round with a log path; COMPILED = release build OK (`crates/build-logs/`) and
Rust tests pass (`crates/TEST_RESULTS.md`), header claims PORTED/parity but
Lane D did not re-run the equivalence; WRITTEN = port code present, equivalence
not re-run or header does not claim PORTED; NOT BUILT = no counterpart.
No pair is VERIFIED except `relay` (HTTP black-box); nothing below changes the
shipped image (all pairs: in-image side is the Node/Python original).

| Crate | Counterpart (live, in image) | Status | Evidence |
|---|---|---|---|
| `relay` | `relay/relay.mjs` + README (Node stdlib-only; `RELAY_PORT` 8787, `RELAY_STORE_FILE`; UI clients `relay/viewer.html`, `board/board.html` watermark-poll `?since=`) | VERIFIED with 5 diffs | `crates/verify-logs/relay-blackbox.log`. 15/22 cases byte-identical plus viewer-HTML same (16/22); diffs R1–R5 below (`/health` rooms count is a state artifact). UI's own suites: `relay.test.mjs` 43/43; `relay.round13.test.mjs` 24/25 (R13-419 fails vs Node itself — stale clamp expectation, pre-existing). |
| `assess-server` | `server/server.mjs` + `server/assess.mjs` + `server/model.mjs` + `server/queue.mjs` | WRITTEN | Header states partial port (no crew/cameras/fires/radar routes). COMPILED + tests 46/46, but surface mismatch is declared, so not a drop-in pair. |
| `queue-core` | `server/queue/queue_service.py` (`validate_envelope`) | COMPILED | Build EXIT=0, tests 54/54. Equivalence per header claim, not re-run here. |
| `queue-store` | `server/queue/trio_repo.py`, `server/queue/trio_store.py` | COMPILED | Build EXIT=0, tests 48/48. |
| `agent-runtime` | `server/queue/trio_agent.py` | WRITTEN | Builds, but 1 Rust test fails on live data (`agents/registry.json` entry 0 empty `command`; see TEST_RESULTS.md). Pair equivalence not re-run. |
| `guardrail` | `server/queue/spark_gen.py`, `server/queue/spark_guardrail.py` | COMPILED | Build EXIT=0, tests 49/49. |
| `stack` | `run-stack.sh` | COMPILED | Build EXIT=0, tests 43/43. Planner only, never spawns — same scope as shell. |
| `dashboard` | `os/docs/DASHBOARD_SPEC.md`, `os/tests/test_crewboard_*.py`, `test_dashboard_*.py` | COMPILED | Build EXIT=0, tests 138/138. |
| `intel` (B09–B14) | `os/intel/` package (+ `os/intel.py`) | WRITTEN | Lib builds; `tests/edge_cases.rs` + `tests/error_paths.rs` do not compile (E0063), so `cargo test -p intel` runs 0 tests. |
| `os-jobs` | `os/jobs.py` + jobs unit tests | COMPILED | Build EXIT=0, tests 181/181; header: PORTED. |
| `os-memory` | `os/mos/memory.py` + memory tests | COMPILED | Build EXIT=0, tests 72/72. |
| `os-identity` | `os/mos/capabilities.py` | COMPILED | Build EXIT=0, tests 59/59. |
| `os-workspace` | `os/mos/artifact_store.py`, `os/mos/gitops.py` | COMPILED | Build EXIT=0, tests 77/77. |
| `os-budget` | `os/intel/budgets.py`, `cost_check.py`, `brief_cost_check.py`, drills, `os/mos/disk_audit.py` | COMPILED | Build EXIT=0, tests 125/125. |
| `os-supervisor` | `os/intel/watchman_*.py`, `watchdog*.py`, `kill_worker.py` | COMPILED | Build EXIT=0, tests 433/433. |
| `os-worker` | `os/mos/worker.py`, `os/os/drivers/*_driver.py`, `os/os/uplink/relay_uplink.py` | COMPILED | Build EXIT=0, tests 133/133. |
| `os-boot` | `os/mos.py`, `os/mos/cli.py`, `os/os/bin/metaos-*`, `os/os/build-*.sh` | COMPILED | Build EXIT=0, tests 62/62. |
| `os-misc` (B24–B27 ported; B28–B30 carried) | `os/poll.py`, `presence.py`, `send.py`, `store.py`, `watch*.py`, `announce/clipboard/edits/forward/paste/saved.py`, `admin/digest/export/health/timecapsule/webhook.py`, `os/worlds/validate_pack.py` | COMPILED | Build EXIT=0, tests 83/83. B28–B30 are carried-as-data, no code pair. |
| `agent-ops` | none identified (operator subsystems; no single original) | NOT BUILT (pair) | Crate itself COMPILES (EXIT=0); no tests/; no counterpart to verify against. |
| `parity-tests` | n/a (harness by design) | NOT BUILT (pair) | Tests 237/237; harness, no live counterpart. |

## Relay diffs R1–R5 (VERIFIED, `crates/verify-logs/relay-blackbox.log`)

- R1 — POST `/rooms/<room>/messages` returns `{"index":N}` only; Node returns
  `{"index":N,"id":"msg-<16 hex>"}` (stable digest; documented `relay/relay.mjs:34`).
- R2 — POST body with whitespace after `,` (e.g. Python `json.dumps` default,
  pretty-printed JSON) → Rust 400 `{"error":"request body is not valid JSON"}`,
  Node 201. Root cause: `parse_object_strings` in `crates/relay/src/http.rs`
  never calls `skip_ws` after consuming `,` before the next key.
- R3 — GET with unparseable/invalid `since` (e.g. `since=abc`) → Node 400
  `{"error":"since must be -1 or a non-negative integer"}`, Rust 200 full room.
- R4 — GET `limit` is ignored by Rust (returns whole room); Node applies
  `slice(0, limit)`.
- R5 — GET out-of-range `limit` (e.g. 99999) → Node 400, Rust 200 full room.
- Non-diff note: `/health` `rooms` counts differ only by accumulated test rooms
  (state artifact, same shape); viewer HTML, message/notify line formats,
  `ts` fields, all 8 validation refusals, and 404s are byte-identical in shape.
- Current UI clients (`relay/viewer.html:218`, `board/board.html:263`) only use
  POST messages + `GET ?since=` watermark polling — R4/R5 are latent for them,
  R1/R2 are live for any non-`JSON.stringify` poster (R2) or `id` reader (R1).
