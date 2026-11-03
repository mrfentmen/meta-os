# Meta Hospital eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/hospital/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| HOSP-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-XWORLD-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| HOSP-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| HOSP-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/hospital/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including HOSP-XWORLD-01, whose passing
evidence names the clean own-declaration picture (receives 2/2,
sends 2/2), and HOSP-XWORLD-02, whose passing evidence names the
other-side gaps rather than hiding them: ems sends
`multi-casualty-summary` to hospital with no matching hospital receive,
and nypd declares receiving `capacity-status` from hospital with no
matching hospital send.
