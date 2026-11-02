# `dashboard` — behaviour record (B145, 2026-11-02)

Crate: `crates/dashboard` (package `dashboard`, edition 2021, no
dependencies). Module map: `src/lib.rs:1-61` exports one public
module, `contract`; all behaviour lives in `src/contract.rs`.

This is a **pure contract library**. It does no I/O, holds no state,
starts no thread, reads no environment variable, and writes nothing.
Every value it reports comes from its arguments; every time value is
passed in (`now`), never read from a clock.

## 1. Brief payload and staleness (BRF-042 / BRF-043)

- Brief kinds are exactly `morning`, `onjoin`, `ondemand`
  (`contract.rs:26`).
- `BriefPayload` (`contract.rs:39-47`) carries `id`, `room`, `kind`,
  `generated_at`, `age_seconds`, `template`.
- `validate_brief_payload` (`contract.rs:49-62`) refuses, in this
  order: an unknown kind (`bad brief kind: <kind>`), an id that is not
  `brief:<room>:<generated_at>` (`bad brief id: <id>`), then an empty
  room, a negative `generated_at`, or a negative `age_seconds`
  (`bad brief timestamps`).
- Staleness begins at exactly 7200 seconds (`is_stale`,
  `contract.rs:69-72`); `stale_label` (`contract.rs:75-80`) returns
  `None` while fresh and `"<human age> old — regenerate for current
  state"` once stale.
- `template_marker` (`contract.rs:64-67`) returns `Some("TEMPLATE")`
  for a template brief, never letting it look Spark-written.

## 2. Palette and accessibility (DSH-018 / DSH-019)

- Six foregrounds (`contract.rs:91-99`) and two panel backgrounds
  (`contract.rs:101`) are the whole palette.
- `wcag_luminance` (`contract.rs:105-116`) implements the WCAG
  relative-luminance formula; `wcag_contrast_ratio`
  (`contract.rs:118-122`) returns `(max+0.05)/(min+0.05)`.
- No guard exists for a colour shorter than `#rrggbb`: see Findings.

## 3. Verdicts and Brief sections (STR-004 / DSH-031 / INT-025)

- `VERDICTS` lists `build ok`, `build broken`, `unclear`
  (`contract.rs:32`). `verdict_icon` (`contract.rs:124-131`) maps
  those three and renders any unknown verdict verbatim with `?` —
  it never invents a fourth state.
- `BRIEF_SECTION_ORDER` (`contract.rs:143-144`) is `decisions`,
  `in_flight`, `owners`, `blocked`, `watch_items`.
- `brief_section_title` (`contract.rs:148-158`) maps those keys to
  the pinned display titles and returns `None` for an unknown key.
- `default_open` (`contract.rs:134-136`) opens only `blocked`.

## 4. Alerts feed (DSH-013)

- `AlertCard` (`contract.rs:162-167`) is `id`, `created_at`,
  `resolved`.
- `alerts_feed` (`contract.rs:169-173`) sorts newest first, ties
  broken on id descending, using Rust's stable `sort_by`.
- `addressable_cards` (`contract.rs:175-178`) drops resolved cards;
  only open cards are addressable.

## 5. Deep links and demo mode (DSH-022 / DSH-028)

- `parse_deep_link` (`contract.rs:189-206`) accepts only
  `#intel/brief/<id>` and `#intel/alert/<id>` with a non-empty id.
  Everything else, including a missing `#`, is `None`.
- `resolve_brief_link` (`contract.rs:208-211`) parses the id as an
  `i64` and returns it only when it is present in the history window.
- `demo_mode_on` (`contract.rs:214-221`) turns demo mode on only for
  an exact `demo=1` pair; `demo=10` and a bare `demo` stay off.

## 6. Today counters (DSH-032)

- `TodayCounts` (`contract.rs:224-230`): jobs done, briefs, alerts
  fired, alerts resolved.
- `today_counts` (`contract.rs:232-251`) dedupes brief timestamps.
- `same_day` (`contract.rs:254-258`) compares UTC calendar days
  (`div_euclid(86400)`).
- `count_today_records` (`contract.rs:281-319`) counts only jobs with
  status `done` and a same-day `done_at`; briefs are distinct same-day
  timestamps across history plus the current brief (a brief that is
  also the newest history entry counts once); alerts count a same-day
  `created_at` as fired and a same-day `resolved_at` as resolved,
  independently.
- `today_line` (`contract.rs:321-327`) renders the exact header strip
  wording.

## 7. Error rows (DSH-021)

`SourceError` (`contract.rs:332-336`) has two states, and
`error_row` (`contract.rs:339-349`) renders one sentence each:

- `TokenRejected`: `No token, or this token can't read <panel>. Paste
  a token above to load <panel>.`
- `Unreachable`: `Can't reach the bus store — <panel> is paused. The
  log above is unaffected.`

## 8. Posting gates (GOV-002 / DSH-038 / DSP-040)

- `brief_me_now_enabled` (`contract.rs:351-353`) is `(false, "posting
  is off for this build")`.
- `dispatch_approve_is_request_only` (`contract.rs:356-358`) is
  `true`; `dispatch_may_auto_post` (`contract.rs:361-363`) is
  `false`.
- `alert_write_enabled` (`contract.rs:777-779`) is `(false, "posting
  is off for this build")`.

## 9. Rollback runbook (INT-031)

- `ROLLBACK_STEPS` (`contract.rs:366-371`) pins the four dashboard
  steps.
- `rollback_runbook_ok` (`contract.rs:377-405`) refuses, in order, a
  missing step, a missing `successfully built` rule, a missing
  `Preview deployments are **not** valid` rule, a missing Cloudflare
  docs URL, and a missing `Previous production deployment id` field.
  The first miss is the returned error.

## 10. Crew-board §7 rules (DSH-023/024/025, OS-084)

- `html_escape` (`contract.rs:407-420`) escapes `&`, `<`, `>` with
  `&` first; `route_encode_id` (`contract.rs:423-436`) percent-encodes
  everything outside `[A-Za-z0-9-_.~]`.
- `CrewAlert` (`contract.rs:438-447`) and `alert_ribbon`
  (`contract.rs:473-496`): only an open or acknowledged **critical**
  alert naming the job ribbons; the first such alert wins; the link is
  `bus.html#intel/alert/<encoded id>` only when the alert has an id.
- `attempts_badge` (`contract.rs:508-527`): needs both fields to
  parse as integers; neutral below `max-1`, warn at `max-1`, danger at
  `max` and above.
- `files_line` / `deps_line` (`contract.rs:529-560`): absent or blank
  fields render nothing; files are escaped, deps render `#n`.
- `Artifact` (`contract.rs:567-573`) and `artifact_link`
  (`contract.rs:585-604`) drop absolute paths, `..` segments, empty
  segments, and missing paths; labels are `<file> v<version>`.

## 11. Keyless signing entries

- `py_str_json` (`contract.rs:606-635`) mirrors Python
  `json.dumps(..., ensure_ascii=True)`, including surrogate pairs.
- `is_nonce_hex` (`contract.rs:637-642`) requires exactly 16
  lowercase hex characters.
- `RenameLogEntry`, `NamesHashEntry`, `NamesHistoryEntry`
  (`contract.rs:784-852`) emit keyless JSON with no `sig` key.

## 12. Alert lifecycle (DSH-014 / WDG-014)

- `alert_lifecycle_status` (`contract.rs:667-684`) honours an
  explicit `open`/`acknowledged`/`resolved`; any other status falls
  back to timestamps (`resolved_at`, then `acknowledged_at`, else
  open).
- `acknowledge_alert` (`contract.rs:710-730`): open becomes
  acknowledged and is stamped; re-ack returns `AlreadyAcknowledged`
  without re-stamping; a resolved alert returns `RefusedResolved`; a
  missing id returns `NotFound`.
- `resolve_alert` (`contract.rs:735-748`): open/acknowledged becomes
  resolved and keeps any ack stamp; re-resolve returns
  `AlreadyResolved`; missing id is `NotFound`.
- `unresolved_critical_count` (`contract.rs:753-762`) counts only
  unresolved criticals, case-insensitively; `resolved_count`
  (`contract.rs:767-772`) counts resolved records.

## 13. What it writes

Nothing. There is no `std::fs`, no `std::net`, no `std::env`, no
`println!`, and no global mutable state in either source file. The
only files the crate touches are the fixture documents compiled into
the **tests** with `include_str!`
(`crates/dashboard/tests/b15_spec_notes.rs:26-27`,
`b15_parity.rs:142-143`).

## 14. Refusals — the complete set

| Function | Refusal | Exact result |
|---|---|---|
| `validate_brief_payload` | unknown kind | `Err("bad brief kind: <kind>")` |
| `validate_brief_payload` | id mismatch | `Err("bad brief id: <id>")` |
| `validate_brief_payload` | empty room / negative timestamps | `Err("bad brief timestamps")` |
| `rollback_runbook_ok` | missing step | `Err("missing rollback step: <step>")` |
| `rollback_runbook_ok` | missing target rule | `Err("missing valid-target rule")` |
| `rollback_runbook_ok` | missing preview rule | `Err("missing preview-invalid rule")` |
| `rollback_runbook_ok` | missing docs | `Err("missing official docs citation")` |
| `rollback_runbook_ok` | missing id field | `Err("previous deployment id not explicitly addressed")` |
| `parse_deep_link` | anything not intel / empty id | `None` |
| `resolve_brief_link` | non-numeric or absent id | `None` |
| `attempts_badge` | absent / blank / non-numeric | `None` |
| `artifact_link` | absolute / `..` / empty segment / no path | `None` |
| `acknowledge_alert` | resolved record | `RefusedResolved` |
| `acknowledge_alert` | already acknowledged | `AlreadyAcknowledged` |
| `acknowledge_alert` / `resolve_alert` | unknown id | `NotFound` |
| `resolve_alert` | already resolved | `AlreadyResolved` |

## 15. Findings (reported, not fixed)

1. **`wcag_luminance` panics on a short colour.** `contract.rs:105-116`
   slices `hex[1..3]`, `hex[3..5]`, `hex[5..7]` with no length guard.
   `"#fff"` panics; `"#zzzzzz"` silently reads as black. The doc
   promises `#rrggbb`, but the function does not refuse anything else.
   Pinned by `tests/error_paths.rs::a_short_colour_panics_in_the_wcag_helper`.
2. **`human_age`'s sub-hour branch is unreachable.** `contract.rs:82-89`
   handles `secs < 3600`, but its only caller, `stale_label`
   (`contract.rs:75-80`), is gated by `is_stale` at 7200 seconds.
   Dead branch, not reachable from the public API. The same helper
   also produces `"2 h 0 min old"` (the hours branch has no "ago"),
   which reads oddly but is the ported behaviour.
3. **`resolve_brief_link` accepts only numeric ids**
   (`contract.rs:208-211`), while `BriefPayload.id` is
   `brief:<room>:<ts>` (`contract.rs:49-62`). A deep link built from
   a payload id never resolves. No test covers that combination.
4. **`VERDICTS` is dead surface.** The constant is defined
   (`contract.rs:32`) but `verdict_icon` (`contract.rs:124-131`)
   hardcodes the same three strings, so the two can drift.
5. **Two today-count implementations.** `today_counts`
   (`contract.rs:232-251`) and `count_today_records`
   (`contract.rs:281-319`) both compute the same record; the former
   has no production caller, only the in-file unit test.
6. **UTC day vs the viewer's local day.** `same_day`
   (`contract.rs:254-258`) is documented as a deliberate deviation
   from the viewer's local date; it is only safe because the Python
   fixtures are zone-agnostic. A fixture near local midnight would
   disagree with the viewer.
7. **`lib.rs` called a complete crate a skeleton.** The header said
   "skeleton (B00)" and "no logic yet"; this pass corrected it to the
   B15 backend contract (`src/lib.rs:1`). Code unchanged.

## 16. Behaviour covered on disk

Existing: `tests/b15_parity.rs` (26 tests), `b15_crewboard.rs`
(23), `b15_spec_notes.rs` (20), `b15_rollback_parity.rs` (5), plus 7
unit tests in `contract.rs`.

Added by this pass: `tests/error_paths.rs` (refusal messages,
including the panic branch), `tests/edge_cases.rs` (empty / maximum /
duplicate / out-of-order), `tests/gap_close.rs` (helpers and
constants no existing file exercised directly).
