# OC2B-043 — Upgrade behaviour (new version picks up old ledgers)

No schema migration in tree because no schema version exists: incidents
grow by timeline-append, `events/dispatches/model_receipts` JSONL are
`"a"`-appends never rewritten, job results are `trio:<jid>:result` keys +
SQLite rows read back by id with no version gate.

Upgrade: install new checkout, re-run `sh agent-layer/install.sh`
(units fresh, `OC2_CHECKOUT` refreshed, re-enabled). Rollback:
`git checkout <PREV_SHA> -- agent-layer/ && sh agent-layer/install.sh`
(code rolls back, data untouched). Verify: queue depth equal
before/after, units active, `py_compile` clean.
