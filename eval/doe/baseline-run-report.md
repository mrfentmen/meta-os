# Meta DOE eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/doe/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| DOE-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-XWORLD-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| DOE-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| DOE-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/doe/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including DOE-XWORLD-01, whose passing
evidence names the gappy own-declaration picture (receives 1/3,
sends 0/1), and DOE-XWORLD-02, whose passing evidence names the
other-side emptiness rather than hiding it: the only other send to
doe (dep water-advisory) is matched, and no other pack declares a
receive from doe at all.
