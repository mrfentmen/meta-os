# Custos eval — baseline run report (first slice, main af457ebd)

Baseline: the empty-outcome fixture (eval/custos/baseline.mjs), which
predicts nothing happened for every scenario.

| scenario | baseline | honest answer |
|---|---|---|
| CU-KEV-01 | FAIL | 1 red KEV observation, 1 SIMULATED escalation |
| CU-KEV-DEDUPE-01 | FAIL | run1 1 KEV obs, run2 0 |
| CU-KEV-AGE-01 | FAIL | oldest first (2021-11-03, then 2024-05-01), both aged |
| CU-CT-01 | FAIL | 1 yellow certificate-issued, 0 escalations |
| CU-CT-DEDUPE-01 | FAIL | run1 1 CT obs, run2 0 |
| CU-DNS-01 | FAIL | run1 silent, run2 1 yellow drift with diff |
| CU-FP-01 | FAIL | 1 dismissed record, 0 re-raised, 0 escalations |
| CU-CERT-01 | FAIL | expiring / expired / baseline on the tier boundary |
| CU-EXPOSURE-01 | FAIL | 1 yellow exposure (port 3306), 1 red service down |
| CU-HEADERS-01 | FAIL | 3 headers missing (yellow), all five baseline |
| CU-TLS-01 | FAIL | TLSv1.1 drift (yellow), TLSv1.3 baseline |
| CU-SUBDOMAIN-01 | FAIL | outside expected network yellow, inside baseline |
| CU-DEDUP-01 | FAIL | run2 headers-missing suppressed, dedup_suppressed 1 |
| CU-SCHED-01 | FAIL | cycle1 runs due sources, cycle2 runs nothing |
| CU-PACK-01 | FAIL | validator exit 0, never_carries declared |
| CU-EMPTY-01 | PASS | summary only, 0 escalations, 0 errors |

Baseline total: 1/16. Real run total: 16/16. The single baseline
pass is the row that is empty by construction and proves nothing on
its own.
