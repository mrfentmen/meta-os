# Meta MTA eval — baseline run report (first slice)

Baseline: the label-only reader in `baseline.mjs`. It claims the pack
is `spec` and reads nothing else. Run with
`node eval/mta/run.mjs --baseline`; that mode always exits 0 because
its failures are the point.

## Baseline result: 1/11

| ID | Result |
| --- | --- |
| MTA-VAL-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-WATCH-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-ALERT-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-PRIV-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-PRIV-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-XWORLD-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-XWORLD-02 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-FIRST-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-STATUS-01 | PASS — label-only reader: claims spec, reads nothing (label matches by chant) |
| MTA-PRIVCLASSES-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |
| MTA-DOC-01 | fail — label-only reader: claims spec, reads nothing (this scenario needs a read) |

## Real run, for comparison: 11/11

Run with `node eval/mta/run.mjs` (exit 0). All eleven scenarios pass
on the committed packs, including MTA-XWORLD-01, whose passing
evidence names the gappy own-declaration picture (receives 2/3,
sends 0/3), and MTA-XWORLD-02, whose passing evidence names the
other-side gaps rather than hiding them: doe and dsny both declare
receiving `service-diversion` from mta, but mta declares no
`service-diversion` send to either.
