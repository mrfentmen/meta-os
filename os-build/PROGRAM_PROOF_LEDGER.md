# PROGRAM PROOF LEDGER — wave 2, 2026-11-02 (Bond)

Machine: 8GB Mac. Repo HEAD `78862a5` for working-tree runs; clean clone
`c7aeb16` for the light gate. Every row below was run here unless the
status says otherwise. Logs: `os-build/bond-evidence/logs/`.

| # | Program | Exact command | Result | Date | Evidence |
|---|---|---|---|---|---|
| 1 | Imperium queue suite | `python3 -m pytest tests/queue-python -q` | 277 passed, exit 0 | 2026-11-02 | `logs/queue-python-final.log` |
| 2 | Imperium products + schema | `node --test tests/product-parity.test.mjs tests/schema-enforcement.test.mjs` | 15 pass, 0 fail | 2026-11-02 | `logs/imperium-products.log` |
| 3 | Science Lab (Hortus) | `python3 -m pytest os/tests/test_hortus_engine.py os/tests/test_hortus_calibration.py -q` | 14 passed | 2026-11-02 | `logs/science-hortus.log` |
| 4 | Officina | `python3 -m pytest tests/officina -q` | 49 passed | 2026-11-02 | `logs/officina-python.log` |
| 5 | Musica | `node --test tests/musica-*.test.mjs` | 37 pass, 2 fail | 2026-11-02 | `logs/musica.log` |
| 6 | Aegis | module load check of `aegis/*.mjs` | all load; no self-check entry point exists | 2026-11-02 | transcript; `aegis/run-*.mjs` are scanners |
| 7 | Nervus | read `nervus/` | no model-modification claim found | 2026-11-02 | CODE-INSPECTED |
| 8 | Agent runtime | `node --test tests/agents-runtime.test.mjs` | 7 pass, 0 fail | 2026-11-02 | `logs/agents-runtime.log` |
| 9 | Watchman | `node --test tests/agents-watchman.test.mjs` | 3 pass, 0 fail | 2026-11-02 | `logs/agents-watchman.log` |
| 10 | Baton + bridge | `node --test tests/agents-baton.test.mjs tests/agents-bridge.test.mjs` | 2 + 6 pass, 0 fail | 2026-11-02 | `logs/agents-baton.log`, `logs/agents-bridge.log` |
| 11 | Gym | `node --test tests/agents-gym.test.mjs` | 5 pass, 0 fail | 2026-11-02 | `logs/agents-gym.log` |
| 12 | Board | `node --test board/board.test.mjs` | 9 pass, 0 fail | 2026-11-02 | `logs/board.log` |
| 13 | Nuntius relay | `node --test relay/relay.test.mjs` | 7 pass, 0 fail | 2026-11-02 | `logs/relay.log` |
| 14 | Face | `python3 -m http.server 8137` + shell | desktop, Science, Officina windows open | 2026-11-02 | `face-*.png` |
| 15 | Federation | `node --test tests/federation-notice.test.mjs` | 7 pass, 0 fail | 2026-11-02 | `logs/federation.log` |
| 16 | UI-fix audit | `node --test tests/ui-fix-list-audit.test.mjs` | 6 pass, 0 fail | 2026-11-02 | `logs/ui-fix-list.log` |
| 17 | Goose services | `bash services/run-goose-tests.sh` | FAIL: binary absent at hardcoded `/Users/test/...` | 2026-11-02 | `logs/` transcript; BLOCKED-missing-binary |
| 18 | Kernel source | `wc -l kernel/src/*.rs` | 13 files, 5,833 lines | 2026-11-02 | READ-ONLY output in transcript |
| 19 | Crates | listing + test-file grep | 19 crates; 18 have `tests/`, `assess-server` tests live in `src/main.rs` | 2026-11-02 | CODE-INSPECTED |

## Musica failure detail

Both failures are `ModuleNotFoundError: No module named 'pretty_midi'` at
`os/worlds/musica/runtime/midi.py:39`. The midi path cannot run on this
machine until that package exists. This is a missing dependency, not a
test premise error.

## 20. Summary

- **Programs with executed proof:** 13 fully green (1, 2, 3, 4, 8, 9, 10,
  11, 12, 13, 14, 15, 16), plus 1 partial (5, 37/2).
- **Without executed proof:** 6 and 7 (no self-check entry points; read
  only), 17 (blocked on a missing Goose binary), 18 (read-only by rule),
  19 (listing only).
- **Not counted as pass:** anything not run here. The Science Lab cycle
  tests were not run: `os/tests` has 120 collection errors without the
  external `PYTHONPATH` modules.
