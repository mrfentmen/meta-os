# OC2B-011 — data-directory contract

Derived from code constants. All current defaults are REPO-RELATIVE
(beside `server/queue/`); `/var/lib/metaos` paths are the PROPOSED ISO
contract (override via named env var; runtime creates dir if missing per
OC2B-012 proof, owned by lane runner).

| Data | Code constant today | Proposed ISO contract (PROPOSED) | Override |
|---|---|---|---|
| Crew incidents / timeline / events / dispatches | `crew_records.data_dir()` = `$TRIO_CREW_DATA_DIR` else `server/queue/crew-data/` | `/var/lib/metaos/crew-data/` | `TRIO_CREW_DATA_DIR` |
| Queue jobs SQLite fallback | `$TRIO_LOCAL_DB` else `server/queue/trio-queue-local.db` | `/var/lib/metaos/trio-queue-local.db` | `TRIO_LOCAL_DB`, `TRIO_STORE=local` forces fallback |
| Spend guardrail ledger | `spark_guardrail.STATE_PATH` = `server/queue/spark_guardrail_state.json` (no env override; `load_state(path)` param only for tests) | `/var/lib/metaos/spark_guardrail_state.json` | PROPOSED: add `SPARK_GUARDRAIL_STATE` env (gap recorded, not hidden) |
| Model receipts JSONL | `models._receipts_path()` = `$METAOS_MODEL_RECEIPTS` else `server/queue/model_receipts.jsonl` | `/var/lib/metaos/model_receipts.jsonl` | `METAOS_MODEL_RECEIPTS` |
| Livecam snapshots + readings | `livecams --out` else `server/queue/livecam_records/` | `/var/lib/metaos/livecam_records/` | `--out` flag |
| Job namespace (not a path) | `trio_store.NS` = `$TRIO_JOB_NS` else `trio` | unchanged | `TRIO_JOB_NS` |

Notes: `crew_records.data_dir()` is the read path shared with
`server/crew-status.mjs`; result keys always `trio:<jid>:result`.
Nothing writes outside these paths + stdout/journal except the SQLite
file and JSON/JSONL appends. Receipts are append-only; receipt write
failure never fails the model call (`models._receipt` swallows OSError).
