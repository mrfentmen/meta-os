# Meta Aegis eval — first slice

Source: baseline always-no-detection (fixture). Offline replay of committed records; not a live sweep.

| scenario | kind | pass |
|---|---|---|
| AEG-KEV-01 KEV cross-check reproduction: the recorded run checked 0, flagged 0, excluded 10 non-sweep records | kev-reproduction | yes |
| AEG-LED-01 Findings ledger summary: 10 records, info 2, low 4, medium 4 | ledger-summary | NO |
| AEG-DIFF-01 Sweep diff reproduction: the recorded diff added 0, removed 0, left 5 distinct keys unchanged | sweep-diff | NO |
| AEG-FP-01 False-positive drill reproduction: 3 pinned clean packages, 0 findings, status ran | fp-drill | yes |
| AEG-PARSE-01 Sweep prose parse: a hit record parses to one hit, not a clean bill | parse-hit | NO |

Reproduction: 2/5 scenarios replay to their recorded values.
Detection (scored scenarios only): TP 0, FP 0, TN 2, FN 1; precision null, recall 0.
