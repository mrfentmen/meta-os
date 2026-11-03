# Meta DEP eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/dep/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| DEP-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-XWORLD-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| DEP-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DEP-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/dep/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including DEP-XWORLD-01, whose passing
evidence names the gappy own-declaration picture (receives 0/2,
sends 2/2), and DEP-XWORLD-02, whose passing evidence names the
other-side emptiness rather than hiding it: no other pack sends to
dep at all, and the only other receives from dep (doe and mta,
water-advisory) are matched.
