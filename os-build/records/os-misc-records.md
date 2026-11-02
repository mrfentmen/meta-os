# Worked records — every shape `crates/os-misc` writes

B210 deliverable. One real example of each record the crate produces,
annotated field by field. The crate writes no "ledger" of its own; the
append-only JSONL message store is the record log, and `par_clock`'s
`ledger` is an in-memory dedupe set of keys, not a persisted log.

## 1. Stored bus message — `Entry`

Written by `MessageStore::append` (`b24/store.rs:105-127`); one JSON
object per line.

```json
{"id":"build-x-1","room":"build-x","nick":"milo","text":"ship it monday","ts":1758300002,"edited":false,"edit_history":[]}
```

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `<counter>` in the default room, `<room>-<counter>` otherwise (`make_id`, `:57-63`) |
| `room` | string | the store's room, `""` for the default list |
| `nick` | string | author as supplied |
| `text` | string | message body; no length cap at this layer |
| `ts` | integer | caller's timestamp, or `now_ts()` when `None` (`:105-118`) |
| `edited` | bool | false on append, true after `edit` |
| `edit_history` | array | `EditRecord` list, oldest first |

## 2. Edit history record — `EditRecord`

Pushed by `MessageStore::edit` (`b24/store.rs:129-158`).

```json
{"text":"ship it friday","ts":1758299000}
```

| Field | Meaning |
|---|---|
| `text` | the displaced text, verbatim |
| `ts` | the edit's timestamp, caller-supplied or now |

## 3. Poll outcome — `PollOutcome`

Returned by `poll_one` (`b24/poll.rs:14-22`, `76-90`). Not serialized;
the CLI prints `all`/`new_from_others` and logs warnings.

```text
PollOutcome {
  all: ["pax: hello", "milo: hi"],
  new_from_others: ["pax: hello"],
  warnings: ["presence heartbeat failed: beat-down"]
}
```

| Field | Meaning |
|---|---|
| `all` | every line `bus_get` returned, including own lines |
| `new_from_others` | lines whose `<prefix>:` is not one of `own_prefixes` |
| `warnings` | non-fatal heartbeat / seen-write / receipt failures |

## 4. Watch display row — `Shown`

Produced by `watch_once` (`b24/watch.rs:19-22`, `66-71`).

```text
Shown { room: "muse-bus:room:news", line: "pax: hello" }
```

| Field | Meaning |
|---|---|
| `room` | the bus key the line came from (key, not a display label) |
| `line` | the raw line as received |

## 5. Saved bookmark — `SavedEntry`

Shape used by `saved` (`b25/saved.rs:25-33`); rendering and filtering
only — persistence is not carried (gap G12).

```text
SavedEntry { id: "n-1", room: "news", nick: "alice", text: "x", ts: None, saved_ts: 2 }
```

| Field | Meaning |
|---|---|
| `id` | message id in its room |
| `room` | `""` = main, otherwise the room name |
| `nick` | original author |
| `text` | original text at save time |
| `ts` | original message timestamp, optional |
| `saved_ts` | when the bookmark was made |

Rendered line (`render_line`, `:35-38`):
`[n-1] #news alice: x`.

## 6. PAR clock alert — `AlertEvent`

Produced by `tick` (`b27/par_clock.rs:48-61`, `148-195`).

```text
AlertEvent {
  kind: "crew-unaccounted",
  severity: "critical",
  urgency: "life-safety",
  alert_id: "par-unaccounted-crew-2-1600",
  crew: "crew-2",
  due_at: 1600,
  entered_at: 1000,
  ts: 1800,
  explanation: "No completed PAR for crew crew-2 and the grace window has passed (3 minutes overdue). Treat as a mayday-standard check failure.",
  suggested_fix: "Escalate to the incident commander now. Do not let this clock clear itself; only a confirmed PAR check or an exit clears it.",
  location: null
}
```

| Field | Meaning |
|---|---|
| `kind` | `par-check-due` or `crew-unaccounted` |
| `severity` | `warning` for the first, `critical` for the second |
| `urgency` | `urgent` or `life-safety` |
| `alert_id` | `par-due-<crew>-<due_at>` / `par-unaccounted-<crew>-<due_at>`; no spaces |
| `due_at` | base (last PAR or entry) + interval |
| `entered_at` | the crew's entry timestamp |
| `ts` | the tick's `now` |
| `explanation` | human text, includes seconds/minutes overdue |
| `suggested_fix` | the required next action |
| `location` | copy of the crew record's location |

Frozen line rendered by `render_alert` (`:249-251`):
`ALERT:par-unaccounted-crew-2-1600 critical crew-unaccounted`.

Timeline events (`TimelineEvent`, `:33-39`) are the same state log in
memory: `{ kind: "par-enter"|"par-complete"|"par-exit", crew, ts, location }`.

## 7. Markdown export

`write_md` (`b26/export.rs:25-33`):

```markdown
# Export of #news

## milo (ts:1758300002) (edited)

ship it monday

```

`fmt_time` is a placeholder (`:14-23`): `ts:<seconds>`, or
`unknown time` when the timestamp is absent/negative. Python formats
local time (`os/export.py:54-60`); gap G15.

## 8. JSONL export line

`write_json_line` (`b26/export.rs:35-50`):

```json
{"nick":"milo","text":"hi","ts":1,"edited":true}
```

`ts` is `null` when absent; `edited` is omitted unless true.

## 9. Webhook payload

`payload_for` (`b26/webhook.rs:37-49`):

```json
{"nick":"milo","text":"ship it","room":"#news","ts":1758300002}
```

Only `\` and `"` are escaped; newlines are **not** escaped here, unlike
the export writer. That is the code as written; delivery is gap G18.

## 10. Health line

`health_text` (`b26/health.rs:22-26`):

```text
HEALTH cpu=12% mem=46% disk=70% up=3d4h12m load=0.42
```

`cpu/mem/disk` use `{:.0}%`; `load` uses `{:.2}`; `up` is
`uptime_str(total_secs)`.

## 11. Pack validation error list

`validate_pack` (`b27/validate.rs:48-313`) returns `Vec<String>`; empty
means valid. Example from a manifest with a duplicate watcher and a bad
severity:

```text
["duplicate watcher id: w1", "alerts[0].severity must be one of critical, warning"]
```

Errors are appended in check order: required keys first (returning early
when any are missing), then pack/names/status, watchers, agents, alerts,
privacy classes, cross-world, firstboot, urgency.
