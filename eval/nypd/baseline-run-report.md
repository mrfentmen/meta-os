# Meta NYPD eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/nypd/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/10

| ID | Result |
| --- | --- |
| NYPD-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| NYPD-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| NYPD-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 10/10

Run with `node eval/nypd/run.mjs` (exit 0). All ten scenarios pass
on the committed packs, including NYPD-XWORLD-01, whose passing
evidence names the reciprocity gaps rather than hiding them:
receives 0/3 reciprocated, sends 2/3 reciprocated, with
`incoming-casualty-summary` from fdny, `transport-status` from ems,
and `capacity-status` from hospital all declared as received by nypd
but no such send declared by any source pack, and
`road-closure-summary` to fdny declared as sent by nypd but no such
receive declared by the fdny pack.
