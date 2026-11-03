# Meta Musica eval — baseline run report

Command: `node eval/musica/run.mjs --baseline`
Source: baseline always-reject (fixture) — a do-nothing source that
rejects every take and catalogues nothing.

Result: 1/10 scenarios passed, 9 failed.

| scenario | baseline result |
|---|---|
| MUS-KEEP-01 (hn029 take-001, expected keeper) | fail — baseline predicts reject |
| MUS-KEEP-02 (hn029 take-004, expected reject) | PASS — the only negative scenario |
| MUS-SESS-01 (hn029 counts) | fail — baseline predicts no keepers |
| MUS-SESS-02 (overnight-001 counts) | fail — baseline predicts no keepers |
| MUS-SESS-03 (hn038 brief sessions) | fail — baseline predicts no keepers |
| MUS-VAR-01 (variation calibration) | fail — baseline predicts not-a-clone for the 0.9997 pair |
| MUS-RIGHTS-01 (hn029 rights) | fail — baseline predicts violations, record has none |
| MUS-NORM-01 (hn029 normalisation) | fail — baseline predicts out-of-tolerance |
| MUS-CAT-01 (hn029 catalogue) | fail — baseline predicts an empty catalogue |
| MUS-CAT-02 (overnight-001 catalogue) | fail — baseline predicts an empty catalogue |

Comparison: the real-records run (`node eval/musica/run.mjs`)
passes 10/10 against the same scenario set and the same harness.
These are fixture numbers, not model performance: the baseline's
single pass is the recorded reject row, and beating 1/10 on that
row alone proves nothing. A real run must replay all ten.
