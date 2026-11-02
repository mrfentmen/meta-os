# BOND — WAVE 2 STATUS (2026-11-02)

Machine: 8GB Mac. Repo HEAD at time of run: `78862a5` (clean clone used
`c7aeb16`, then advanced). No kernel source touched. Nothing committed or
pushed.

Statuses: VERIFIED (ran it), CODE-INSPECTED (read it), UNIMPLEMENTED,
BLOCKED (blocker named), PENDING (not reached).

## Section 1 — Program proof ledger

| # | Program | Ran | Result | Evidence |
|---|---|---|---|---|
| 1 | Imperium queue suite | `python3 -m pytest tests/queue-python -q` | 277 passed | `os-build/bond-evidence/logs/queue-python-final.log` |
| 2 | Imperium products + schema | `node --test tests/product-parity.test.mjs tests/schema-enforcement.test.mjs` | 15 pass, 0 fail | `.../logs/imperium-products.log` |
| 3 | Science Lab (Hortus) | `python3 -m pytest os/tests/test_hortus_engine.py os/tests/test_hortus_calibration.py -q` | 14 passed | `.../logs/science-hortus.log` |
| 4 | Officina | `python3 -m pytest tests/officina -q` | 49 passed | `.../logs/officina-python.log` |
| 5 | Musica | `node --test tests/musica-*.test.mjs` | 37 pass, 2 fail | `.../logs/musica.log` — both fail on `ModuleNotFoundError: pretty_midi` (`os/worlds/musica/runtime/midi.py:39`). BLOCKED-missing-dep, not a code fault. |
| 6 | Aegis | module import check for `aegis/*.mjs` | all modules load; no self-check entry point exists | `.../logs/` (see transcript); `aegis/run-*.mjs` are scanners, not self-checks |
| 7 | Nervus | read `nervus/` | no code claims a model was modified; modules are contracts/stub-runner/tray/dose-windows | CODE-INSPECTED |
| 8 | Agent runtime | `node --test tests/agents-runtime.test.mjs` | 7 pass, 0 fail | `.../logs/agents-runtime.log` |
| 9 | Watchman | `node --test tests/agents-watchman.test.mjs` | 3 pass, 0 fail | `.../logs/agents-watchman.log` |
| 10 | Baton + bridge | `node --test tests/agents-baton.test.mjs tests/agents-bridge.test.mjs` | 2 + 6 pass, 0 fail | `.../logs/agents-baton.log`, `agents-bridge.log` |
| 11 | Gym | `node --test tests/agents-gym.test.mjs` | 5 pass, 0 fail | `.../logs/agents-gym.log` |
| 12 | Board | `node --test board/board.test.mjs` | 9 pass, 0 fail | `.../logs/board.log` |
| 13 | Nuntius relay | `node --test relay/relay.test.mjs` | 7 pass, 0 fail | `.../logs/relay.log` |
| 14 | Face | served `os-build/face` on 127.0.0.1:8137, opened shell | dock opens windows; see Section 5 | screenshots in `os-build/bond-evidence/` |
| 15 | Federation | `node --test tests/federation-notice.test.mjs` | 7 pass, 0 fail | `.../logs/federation.log` |
| 16 | UI-fix audit | `node --test tests/ui-fix-list-audit.test.mjs` | 6 pass, 0 fail | `.../logs/ui-fix-list.log` |
| 17 | Goose services | `bash services/run-goose-tests.sh` | FAIL | runner hardcodes `/Users/test/mcp-servers/toolchains/goose-src/build/goose`, absent here. BLOCKED-missing-binary. |
| 18 | Kernel source | `wc -l kernel/src/*.rs` | 13 files, 5833 lines | READ-ONLY |
| 19 | Crates | listing + test-file grep | 19 crates; 18 have `tests/`, `assess-server` keeps its tests in `src/main.rs` | CODE-INSPECTED |
| 20 | Summary | — | 12 programs fully green, 1 partial (Musica, missing dep), 2 blocked (Goose binary, kernel boot), 1 read-only listing (kernel), 1 inspected (Nervus) | this table |

Section 1 did not run the 120 collection-error modules in `os/tests`: those
need `PYTHONPATH` entries (`relay_common`, `trigger_check`, ...) that no
conftest supplies. Only the Hortus files were in scope.

## Section 2 — Second clean gate

- 21. Fresh clone of `main` at `c7aeb16` into `/tmp/wave2-clean`. VERIFIED.
- 22. `bash os-build/gate.sh` → exit 127 at `os-build/gate.sh:16`:
  `qemu-system-x86_64: command not found`. `cargo bootimage` is also not
  installed and only the stable toolchain exists. BLOCKED-no-qemu.
  Log: `/tmp/wave2-clean-gate.log` (not committed).
- 23. Gate result: RED, failing step is the toolchain check (qemu), before
  any build. No boot claim is made.
- 24. Flagged node failures re-ran in the clean clone: the 55 native/Swift
  failures reproduce. Light gate `npm-test`: 2033 tests, 1978 pass, 55 fail.
- 25. `pytest tests/queue-python` in the clean clone: exit 0 (log captured by
  `light_gate.sh` stage 4, `pytest-queue — exit 0`).
- 26. Counts differ from Section 1 only where main advanced (queue 264 → 277);
  no new failure class.
- 27-28. README numbers and program list checked: `os-build/README_AUDIT_BOND.md`.
- 29. Every ledger row above carries an evidence path or a read-only label.
- 30. Gate summary posted here: RED at the toolchain step, no boot claim.

## Section 3 — Model integration

- `os-build/MODEL_INTEGRATION.md` exists (commit 42438dc), `server/queue/models.py` exists.
- Model ids in code match the served list: muse-spark-1.3, muse-wonder-1.0,
  sam-3.1, muse-image-1.0, muse-voice-transcribe-1.0. No other provider ids
  found in `server/` or `os/`.
- `tests/queue-python/test_models.py` + `test_judge_model.py`: 13 passed.
- Receipt writer exists (`models.py:83-101`) but **no receipt artifact is
  committed** and `model_receipts.jsonl` is absent. Receipt-schema claims are
  CODE-INSPECTED, not VERIFIED.
- `~/Desktop/hackathon key.txt`: ABSENT. Tasks 39-42 BLOCKED-no-key.
- Tasks 33-38, 44-45: written in `MODEL_INTEGRATION_EVIDENCE.md`. Receipts absent (CODE-INSPECTED); SAM segment-only; Image/Voice unwired; spend estimates labelled, no artifact.

## Section 4 — Science + Officina reproduction

- No `os-build/OPENCODE2_SCIENCE_STATUS.md`; no completed science cycle ledger
  found. `os-build/SCIENCE_LAB_W2_SLICE1.md` states no cycle has run.
  First-cycle re-run: BLOCKED-no-cycle.
- Officina 2a gate: `python3 os-build/officina_2a_gate.py` → PASS 14/14, exit 0.
  Run artifacts exist in `os/worlds/officina/runs/`.
- Hortus calibration table exists (`.../hortus/calibration/UNCALIBRATED_RESULTS.md`).
- Tasks 46-56: written in `REPRODUCTION_REPORT.md`. Science cycle BLOCKED-no-cycle. Officina gate PASS 14/14; all four dimensions inside bounds.

## Section 5 — Face + image checks

- 57-59. Screenshots: `os-build/bond-evidence/face-desktop-2026-11-02.png`,
  `face-science-window-fixed-2026-11-02.png`,
  `face-officina-window-2026-11-02.png`.
- Science Lab was blank at first: dock points at
  `http://127.0.0.1:18934/labs/molecules/index.html` and nothing listened on
  18934. Starting `python3 -m http.server 18934 --bind 127.0.0.1` from the repo
  root fixed it; the molecule viewer renders.
- 60. Dock entries: Chrome (external), Terminal, Files, Dashboard, Code
  Editor, Notes, Board, Calendar, Calculator, Settings, Trash (all local
  files exist), Imperium, Science Lab, Custos, Officina (all on :18934),
  Musica (`musica.html`). Science Lab clicked and verified; the rest are
  CODE-INSPECTED targets, not clicked one by one.
- 61-63. UTM: BLOCKED-no-utm (not installed).
- Screenshots are dated and under `os-build/bond-evidence/`. VERIFIED.

## Section 6 — Docs accuracy audit

DONE. `os-build/README_AUDIT_BOND.md`. Six stale numbers, one program
(Meta Faber) with no code, Custos shown as built not retired, one loop
scenario failing (11/12), 12 packs not 9.

## Section 7 — Kernel-adjacent reading

DONE. `os-build/BOND_KERNEL_READING.md`. No build-out K-item is marked
done; K2 readkey has a gate log but is not started by `main.rs`; no
filesystem, IPC, or driver logs exist.

## Rules check

- No `kernel/src` edit. No push. One heavy job at a time.
- Every completed row above names a log or artifact.
- Nothing in this file claims a boot or a model call.
