# OC2B-021 — Log locations + rotation policy

## Locations (from unit files + code constants)

| Component | Where output goes |
|---|---|
| oc2-queue.service | stdout/stderr → user journal (`journalctl --user -u oc2-queue`; no `StandardOutput=` override) |
| oc2-trio.service | stdout/stderr → user journal (`journalctl --user -u oc2-trio`; no override) |
| oc2-patrol.service (oneshot) | per-run output → user journal (`journalctl --user -u oc2-patrol`); heartbeat snapshot rewritten each cycle to `crew-status.json` in crew data dir |
| Queue store | `TRIO_LOCAL_DB` else `server/queue/trio-queue-local.db` (SQLite; result envelopes are store keys, not log files) |
| Crew records | `TRIO_CREW_DATA_DIR` else `server/queue/crew-data/`: `incidents.json`, `events.jsonl` + `dispatches.jsonl` (appended), `crew-status.json` (rewritten), `evidence/` |
| Model receipts | `METAOS_MODEL_RECEIPTS` else `server/queue/model_receipts.jsonl` (one JSON object/line, append-only) |
| Guardrail state | `server/queue/spark_guardrail_state.json` (gitignored) |

## Rotation policy

- journald: **systemd default** — no `StandardOutput=`/`MaxRetention`
  overrides ship in any unit; no logrotate config for OC2 ships in the repo.
  Journal behavior on the ISO = image default. VERIFY on the bake, do not
  assume persistent.
- Receipt files (`events.jsonl`, `dispatches.jsonl`,
  `model_receipts.jsonl`): **append-only, no rotation in code** (`"a"`
  opens in `models.py`; "appended, never rewritten" in crew_records).
  Growth bound = patrol volume × retention window; retention rule is
  OC2B-114/OC2B-141's job — currently UNPROVEN, named here honestly.
