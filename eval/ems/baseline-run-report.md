# Meta EMS eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/ems/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/9

| ID | Result |
| --- | --- |
| EMS-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| EMS-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| EMS-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 9/9

Run with `node eval/ems/run.mjs` (exit 0). All nine scenarios pass on
the committed packs, including EMS-XWORLD-01, whose passing evidence
names the reciprocity gap rather than hiding it: receives 3/3
reciprocated, sends 1/3 reciprocated, with `multi-casualty-summary`
to fdny and to hospital not declared as received by either
destination. Adapter tests: 8/8 (`node --test
eval/ems/adapter.test.mjs`).

These are fixture numbers for the baseline and pack-declaration
numbers for the real run, not system performance: the EMS pack is
status `spec`, so there is no runtime performance to rate.
