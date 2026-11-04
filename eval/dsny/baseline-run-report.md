# Meta DSNY eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/dsny/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| DSNY-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-XWORLD-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| DSNY-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DSNY-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/dsny/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including DSNY-XWORLD-01, whose passing
evidence names the gappy own-declaration picture (receives 0/2,
sends 1/2), and DSNY-XWORLD-02, whose passing evidence names the
other-side gaps rather than hiding them: mta and doe send dsny
things it does not declare receiving, while doe and dep expect
road-clearing-status from dsny that dsny sends to nypd and mta only.
