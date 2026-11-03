# OC2B-039 — Log location per service

Condensed from OC2B-logging.md (authoritative for rotation).

| Service | Location |
|---|---|
| oc2-queue | user journal only — stdout/stderr, no `StandardOutput=` override |
| oc2-trio | user journal only — stdout/stderr, no override |
| oc2-patrol (oneshot) | per-run output → user journal + heartbeat `crew-status.json` rewritten each cycle |
| queue store / jobs | `$TRIO_LOCAL_DB` else `server/queue/trio-queue-local.db` (SQLite) |
| crew records | `$TRIO_CREW_DATA_DIR` else `server/queue/crew-data/`: `incidents.json`, `events.jsonl` + `dispatches.jsonl` (appended), `crew-status.json` (rewritten), `evidence/` |
| model receipts | `$METAOS_MODEL_RECEIPTS` else `server/queue/model_receipts.jsonl` (append-only) |
| guardrail state | `server/queue/spark_guardrail_state.json` (gitignored) |

```sh
journalctl --user -u oc2-queue -n 50 --no-pager
journalctl --user -u oc2-trio -n 50 --no-pager
journalctl --user -u oc2-patrol -n 20 --no-pager
```
