# Baselines measured at round-3 start (NC-009)

Main tip merged: 9e50001 (round-3 tip). Branch: opencode/mac-tasks.
Measured on this Mac, 2026-11-01:

- node: 1999 run, 1943 pass, 56 fail — all 56 in tests/native-*,
  zero outside the known WKWebView set.
- cargo: 1412 pass, 0 fail (`cargo test --workspace`, EXIT:0).
- custos: 48/48 (`tests/custos/`, alone).
- officina: 49/49 (`tests/officina/`, alone).
- queue: uncollectable on this Mac (4 collection errors,
  dynamic_credentials); throwaway-with-patch: 110/110 (round-2 proof).
- Environment: node v24.21.0, npm 11.19.0, cargo/rustc 1.99.1,
  python3 system + pytest 8.4.2.

Note: `pytest tests/custos/ tests/officina/` in ONE invocation collides
(both suites ship a test_pack.py with no __init__.py — import file
mismatch). Suites pass individually; combined invocation is a harness
naming quirk, not a code failure.
