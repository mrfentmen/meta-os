# Python records writer — behaviour record (B237)

Module: `server/queue/crew_records.py`. Read 2026-11-02. Every claim
cites the file and line range it comes from.

## What it does

The crew's append-only audit trail (`crew_records.py:1-39`). It owns
four files under a data directory: `incidents.json` (records that only
grow), `events.jsonl` (event feed), `dispatches.jsonl` (SIMULATED
dispatch log), and `crew-status.json` (a rewritten heartbeat snapshot,
not a record), plus per-incident evidence files
(`crew_records.py:4-37`).

Data directory: `TRIO_CREW_DATA_DIR` when set, else `crew-data/` beside
the module (`crew_records.py:46-51`).

## Inputs

- `create_incident(record)` — a record carrying at least `"id"`
  (`crew_records.py:80-93`).
- `append_timeline(incident_id, step)` — one step dict; a step's
  `"status"` advances the record status (`crew_records.py:95-110`).
- `save_evidence_file(incident_id, name, data)` — bytes
  (`crew_records.py:140-148`).
- `attach_evidence(incident_id, entries, at)` — entries carrying
  `"ref"` (`crew_records.py:150-166`).
- `purge_evidence(incident_id, reason, at)` — the false-positive close
  (`crew_records.py:168-208`).
- `append_event(event)`, `append_dispatch(package)`, `write_status(status)`
  (`crew_records.py:210-245`).

## Outputs

- `create_incident` → the stored record, with `"timeline"` defaulted to
  `[]` (`crew_records.py:86-93`).
- `append_timeline` → the updated record; the status is the last step
  status when a step carries one (`crew_records.py:106-109`).
- `list_incidents` → records newest-first by `created_at`, missing
  values last (`crew_records.py:116-120`).
- `open_incidents` → only live statuses: `flagged`, `reported`,
  `candidate`, `under_review`, `investigating`, `monitoring`,
  `response_prepared` (`crew_records.py:122-135`).
- `purge_evidence` → a receipt `{at, reason, files_removed}`
  (`crew_records.py:194-208`).
- `recent_events(limit=60)`, `recent_dispatches(limit=20)` → the last
  `limit` parsed JSONL lines (`crew_records.py:216-230`, `247-258`).
- `read_status()` → the snapshot, or `None` when absent
  (`crew_records.py:240-245`).

## Refusals and durability rules

- A duplicate incident id raises `ValueError` — a second create is a
  bug, not an update (`crew_records.py:83-86`).
- Unknown incident id on append/attach/purge raises `KeyError`
  (`crew_records.py:101-104`, `155-157`, `175-177`).
- Writes to `incidents.json` and `crew-status.json` go through a
  `.tmp` file and `os.replace`, so a reader never sees a half-written
  document (`crew_records.py:74-78`, `232-239`).
- `purge_evidence` deletes only paths that resolve inside the data
  directory; anything else is skipped, never removed
  (`crew_records.py:184-190`).
- A torn final JSONL line is skipped, never fatal
  (`crew_records.py:255-257`).
- Thread safety is one `threading.Lock` per writer instance
  (`crew_records.py:60`, used at every mutation).

## Findings

- `create_incident` indexes `record["id"]` before any validation, so a
  record with no id raises a bare `KeyError` rather than a named
  refusal (`crew_records.py:83-84`). Reported, not fixed: callers own
  the record shape.
- `_load_incidents` does not catch a corrupt `incidents.json`
  (`crew_records.py:66-72`); a malformed file raises
  `json.JSONDecodeError` out of every method that reads it.
- `create_incident` stores a shallow copy (`dict(record)`,
  `crew_records.py:89`); a nested list supplied by the caller can still
  be shared with the stored object until the next load.
- `append_timeline` does not validate that `step` is a dict; a
  non-dict step is appended as-is (`crew_records.py:106`).
