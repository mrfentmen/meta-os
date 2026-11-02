# Aegis false-positive drill

Run `fp-drill-2026-11-02T15-00-49-200Z`. A manifest with three pinned clean packages was swept with a stub source
returning the source's exact clean-answer text.

| item | value |
|---|---|
| status | **ran** |
| packages queried | 3 |
| findings | **0** |
| verdict | **CLEAN, as expected** |

This drills the sweep and the report for false positives. It is not a claim about OSV's data:
the transport was a stub, and the receipt says so.
