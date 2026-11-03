# Meta FDNY eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `partial` and reads nothing else. Run with
`node eval/fdny/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| FDNY-VAL-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-WATCH-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-ALERT-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-PRIV-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-PRIV-02 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-XWORLD-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-FIRST-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-STATUS-01 | PASS — label-only reader: claims partial, reads nothing (label matches by chant) |
| FDNY-RUNTIME-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-PAR-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |
| FDNY-DOC-01 | fail — label-only reader: claims partial, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/fdny/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including FDNY-XWORLD-01, whose passing
evidence names the reciprocity gap rather than hiding it: receives
2/3 reciprocated, sends 2/2 reciprocated, with `transport-status`
from ems not declared as a send by the ems pack. FDNY-PAR-01 passes
on the real PAR clock with its fake clock: due warning, escalation
to critical with the frozen ALERT line, silent deduped repeat.
Adapter tests: 9/9 (`node --test eval/fdny/adapter.test.mjs`).

These are fixture numbers for the baseline and pack-declaration
plus clock-smoke numbers for the real run, not system performance:
the FDNY pack is status `partial`, so only the PAR clock ships as
runtime, and nothing here rates a real fireground.
