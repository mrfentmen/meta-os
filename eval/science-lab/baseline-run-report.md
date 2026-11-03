# Science Lab eval — baseline run report

Recorded 2026-11-03, on branch `hana/science-lab-eval` (stacked on
`hana/science-lab-tools`).

- Runner: `python3 eval/science-lab/run.py`
- Result: **28/28 scenarios pass, 0 fail.**
  - 13 `--check` scenarios: every researcher reads the shipped records.
  - 13 duty scenarios: every duty runs and reports its own check
    (research-director: per-cycle census rows for CYCLE-EXAMPLE-001
    and DRESS-REHEARSAL-001, which carry no check key by design).
  - Registry shape: all 13 entries carry the hosted.py command with
    `hosted: true`.
  - Refusal: unknown agent exits 2 with "it stays a draft".
- Harness tests: `tests/science-lab/test_eval_science_lab.py` 2/2.
- Regression: slice-1 tests 8/8, existing hosted tests 6/6.
- Full report JSON: `eval/science-lab/baseline.json` (deterministic,
  no timestamps).

This is the first Science Lab eval baseline. It guards the wiring,
not science quality: no scenario asserts a hypothesis is true or a
design is sound, because no full hypothesis record file ships on disk.
