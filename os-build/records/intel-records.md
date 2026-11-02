# intel — ledger and record shapes, worked examples (B174)

One real record of each kind the crate writes, annotated field by
field. Values are the ones the constructors produce; no field below is
invented. Line cites name the builder.

## 1. Brief record — `b10_brief::brief::BriefRecord`

Built by `compose_brief` (`brief.rs:505-517`) and validated by
`validate_brief_record` (`brief.rs:47-60`). Stored as JSON under
`<prefix>:intel:brief:<room>:<ts>` (`store.rs:18-20`).

```json
{
  "room": "main",
  "ts": 1762135200,
  "text": "Morning brief for main\n\n## held\nops\n",
  "kind": "morning"
}
```

- `room` — the room the brief belongs to; empty is refused.
- `ts` — unix seconds; negative is refused. `compose_brief` sets `0`;
  the caller that stores it supplies the real timestamp.
- `text` — the composed sections in frozen order; whitespace-only is
  refused.
- `kind` — one of the validator's five names today; see the finding
  that Python allows three.

Announcement line for the stored record: `format_brief_announcement`
returns `BRIEF:<room>:<ts>` (`brief.rs:65-67`).

## 2. Alert record — `b09_core::store::AlertRecord`

Validated by `validate_alert` (`store.rs:53-67`) and written by
`write_alert` (`store.rs:89-113`). Stored as JSON under
`<prefix>:intel:alert:<id>`; index member under
`<prefix>:intel:alert:index` (`store.rs:21-25`).

```json
{
  "id": "presence-stall:milo:job-7",
  "kind": "presence-stall",
  "severity": "critical",
  "room": "main",
  "explanation": "milo holds claimed job job-7 but has been absent ...",
  "created_at": 1762135000,
  "last_seen": 1762135060,
  "status": "open",
  "dedupe_key": "presence-stall:milo:job-7",
  "resolved_at": null,
  "acknowledged_at": null
}
```

- `id`, `kind`, `explanation`, `dedupe_key` — required non-empty.
- `severity` — carried, not validated by this function.
- `created_at` — occurrence start; index score.
- `last_seen` — set to `created_at` when zero on write.
- `status` — `open|acknowledged|resolved`; empty becomes `open`.
- `resolved_at` / `acknowledged_at` — `null` until the matching
  transition.
- Lifecycle: `acknowledge_alert` only moves `open`
  (`store.rs:122-131`); `resolve_alert` moves any existing id
  (`store.rs:132-140`); `auto_resolve_cleared` resolves ids whose
  dedupe key stopped firing (`store.rs:141-152`).

## 3. Plan and job — `b10_brief::dispatch`

`parse_plan` (`dispatch.rs:39-55`) builds the shape; gates read it.

```json
{
  "goal": "ship the release note",
  "jobs": [
    {
      "key": "a",
      "title": "write the note",
      "files": ["intel/release.txt"],
      "deps": [],
      "max_attempts": 3
    }
  ]
}
```

- `goal` — required, trimmed non-empty.
- `key`, `title` — both required per job.
- `files` — shared paths; an unordered duplicate is refused by
  `check_file_overlap`.
- `deps` — must name plan keys; unknown deps and cycles are refused.
- `max_attempts` — `parse_plan` seeds 3; `clamp_attempt_budgets` maps
  ≤0 to 3 and >10 to 10.

## 4. Push — `b10_brief::push::Push`

Built by `build_done_push` / `build_blocked_push`
(`push.rs:58-92`); validated by `validate_push` (`push.rs:102-110`).

```json
{
  "push_type": "done",
  "job_id": "job-7",
  "title": "write the note",
  "text": "All done: write the note (built: intel/release.txt); 2/2 checks passed"
}
```

- `push_type` — exactly `done` or `blocked`; a third type is refused.
- `job_id`, `text` — must be non-empty.
- Done text — names artifacts or says none were recorded, then the
  passed/total check count, or says no criteria were recorded.
- Blocked text — the caller's question if non-empty, otherwise the
  stored note, quoted verbatim.

`PushLedger::decide_push` (`push.rs:119-127`) emits one push per
(job id, type); the second call returns `None`.

## 5. Gate journal — `b09_core::gate::JournalRecord`

`gate_tick` emits two records for one parking (`gate.rs:94-127`):

```json
[
  {
    "dedupe_key": "park:job-7",
    "kind": "parked",
    "job_id": "job-7",
    "text": "Job job-7 blocked on money: need $5"
  },
  {
    "dedupe_key": "escalate:job-7",
    "kind": "blocked-push",
    "job_id": "job-7",
    "text": "Job job-7 blocked on money: need $5"
  }
]
```

- `dedupe_key` — `park:<job>` / `escalate:<job>`; the journal's
  existing `park:` key suppresses a second emission.
- `kind` — `parked` or `blocked-push`.
- `job_id` — the parked job.
- `text` — the question built by `question_for`: `Job <id> blocked on
  <kind>: <note>` for a Dale call, `Job <id> spent its attempt budget`
  otherwise.

## 6. Devpack payloads — `b13_devpack`

### 6a. Brief entry (`brief_entry`, `mod.rs:51-64`)

```json
{
  "generated_at": 1762135000,
  "text": "brief body",
  "as_of": 1762135060,
  "age_seconds": 60
}
```

- Input fields are copied verbatim; `as_of` and `age_seconds` are
  added. `age_seconds = as_of - generated_at`, and can be negative when
  `as_of` predates the record.
- `generated_at` must be `Json::Int`; `as_of` must be `Json::Int`.

### 6b. Plan preview (`plan_preview`, `mod.rs:94-110`)

```json
{
  "summary": "ship it",
  "jobs": [{"key": "a", "title": "A", "files": [], "deps": [], "max_attempts": 3, "accept": [], "req": []}],
  "posting_order": ["a"],
  "jobs_count": 1,
  "max_attempts_total": 3
}
```

- `posting_order` must cover exactly the plan's keys, in any order;
  duplicates or missing keys are refused.
- `jobs_count` is the list length.
- `max_attempts_total` is the arithmetic sum of the jobs' budgets.

### 6c. Alerts feed row (`alerts_feed`, `mod.rs:112-123`)

```json
{"id": "alert-2", "created_at": 1762135100}
```

- Newest first; ties break on id descending.
- Only the two fields exist in this shape.

### 6d. Crew board (`crew_board`, `mod.rs:125-135`)

```json
{
  "presence": ["milo", "hana"],
  "caps": [{"identity": "milo", "bus_post": "true"}],
  "jobs": [{"id": "job-7", "status": "open"}]
}
```

- The three DSH-003 sources are passed through as given; the function
  does not merge, filter, or invent rows.

## 7. Drill report — `b12a_drills`

`DrillReport::new` + `pass_line` (`b12a_drills/mod.rs:34-80`):

```json
{
  "drill": "collision",
  "phases": [
    {"name": "claim", "pass": true, "detail": "first claim won"},
    {"name": "second claim", "pass": true, "detail": "refused"}
  ]
}
```

- `drill` — the module name.
- `phases` — ordered named outcomes; `pass` is the phase verdict.
- `pass_line` — `<drill>: PASS (<n> phases)` only when every phase
  passed; otherwise it names the failed phases.

## 8. Store keys written

From `store.rs:18-35` and `153-160`:

| Key | Kind | Value |
|---|---|---|
| `<prefix>:intel:brief:<room>:<ts>` | string | brief JSON |
| `<prefix>:intel:alert:<id>` | string | alert JSON |
| `<prefix>:intel:alert:index` | sorted set | member id, score created_at |
| `<prefix>:intel:notify:<id>` | string | builder only (not written by `Store`) |
| `<prefix>:intel:notify:index` | sorted set | builder only (not written by `Store`) |
| `<prefix>:intel:dispatch:<id>` | string | dispatch JSON |
| `<prefix>:intel:spend` | string (Rust) / list (Python) | `ts:cents:label` lines |

`<prefix>` is `MUSE_RELAY_KEY_PREFIX` or `muse-bus`
(`store.rs:14-16`).
