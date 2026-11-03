# OC2B-068 — Queue operator doc: start/stop/inspect/drain/retry

All against the packaged tree (`server/queue/`), odd-port pattern for
local runs (`--port 189xx`), tmp `TRIO_LOCAL_DB` for scratch runs.

- start: `python3 server/queue/queue_service.py [--port 8935]` (or
  `systemctl --user start oc2-queue` on target). Verify:
  `curl -s 127.0.0.1:$PORT/health` → 200 `{"ok": true, ...}`.
- stop: `systemctl --user stop oc2-queue` (target) / terminate pid
  (scratch). Idempotent; data kept (SQLite/Upstash persists).
- inspect: `GET /health` (store + fallback named); `GET
  /jobs/<id>/result` → `ok|failed|pending|unknown`; queue depth =
  open-job count in store (`open_job_ids`, OC2B-061/062).
- drain: stop accepting (stop service or firewall port), let trio
  `--once` passes drain filed jobs, confirm depth 0 + all receipted,
  then stop. No loss: receipts persist across restart (proven live:
  OC2B-queue-e2e.json receipt identical before/after restart).
- retry: re-POST same envelope → 200 already-filed (idempotent by
  deterministic id); failed jobs re-file as NEW jobs (new timestamp →
  new id) — no in-place retry counter (see poison note: no quarantine
  logic in tree, OC2B-queue-defects.md).
