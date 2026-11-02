# Wave2 Section 8 — Health (cargo + python)

Date: 2026-11-02. Commands run from /tmp/wave2.

## 1. cargo check
- `cargo check --workspace`: EXIT 0. No errors; warnings only (e.g. parity-tests lib: 140 dead-code warnings for unused helper fns).
- Per-crate `cargo check -p <name>` (19/19): ALL CLEAN, no first-errors to record.
  - CLEAN: agent-runtime, assess-server, dashboard, guardrail, intel, os-boot, os-budget, os-identity, os-jobs, os-memory, os-misc, os-supervisor, os-worker, os-workspace, parity-tests, queue-core, queue-store, relay, stack (19 clean / 0 failing)

## 2. python unittest discover
- `python3 -m unittest discover -s tests/queue-python`: Ran 128 tests — OK (3.7s)
- `python3 -m unittest discover -s tests/officina`: Ran 49 tests — OK (0.03s)
- `python3 -m unittest discover -s tests/custos`: Ran 125 tests — OK (3.9s)
- Total: 302 tests, all OK, 0 failures/errors.
- Note: must omit `-t .` (start dir not importable without it); plain `-s <dir>` works.

## 3. hortus suite (hortus-rung3/)
- No unittest suite present (only run.py / solver.py / nb_batch.py scripts, no test_*.py).
- Live `python3 -u run.py` exceeds 120s (timed out on this host); reference log kept at hortus-rung3/run-output.txt:
  - verify: sim 180.139 W/m vs analytic 181.659 (err 0.84%) and 180.916 (err 0.41%)
  - scoring: champion 733.8 W vs reference 18.3 W at dT=50K; uniform-h check 685.6 W vs 74.0 W
  - verdict: present, long-running (~3+ min) — not re-run to completion here.

## Summary
- cargo: 19/19 crates clean, workspace EXIT 0.
- python: 302/302 pass (128 queue-python + 49 officina + 125 custos).
- hortus: script suite present, no unittest; reference output on file, live run >120s.
