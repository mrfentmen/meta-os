# OC2B-326 — Officina baseline (before 2b/2c/2d)

Date: 2026-11-02. Branch: opencode2/500. Machine: Del's Mac.

Officina suite (python3 -m unittest discover -s tests/officina):

    Ran 49 tests in 0.030s — OK (49 pass, 0 fail)

2a gate (python3 os-build/officina_2a_gate.py):

    GATE: PASS (14/14 clauses)

Both numbers are the pre-change baseline for §§14–16. Later runs
compare against these fixed numbers.

## Post-wiring re-run (OC2B-343)

After wiring 2a->2b (new module prior_art.brief_to_note; 2a modules
untouched) plus new 2c/2d modules and 28 new tests:

    Ran 77 tests in 0.059s — OK (77 pass, 0 fail)
    GATE: PASS (14/14 clauses)

Suite delta is +28 tests, zero regressions. Gate still 14/14.
