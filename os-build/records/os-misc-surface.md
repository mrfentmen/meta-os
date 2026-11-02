# Public surface inventory — `crates/os-misc`

B214 deliverable. Every exported name, one line each, marked used or
unused in the repo today.

Legend: **USED** = called by `crates/parity-tests` (the only executable
caller). **TESTS** = exercised by the crate's own tests only; no
production caller. **DEAD** = no caller and no test.

## b24 — messaging core

| Name | Kind | State |
|---|---|---|
| `MAX_TEXT` | const | TESTS |
| `BusTransport` | trait | TESTS (implemented by test fakes and parity callers) |
| `room_for_key` | fn | TESTS |
| `bus_key` | fn | TESTS |
| `parse_duration` | fn | TESTS |
| `parse_pomodoro_duration` | fn | TESTS |
| `parse_ttl` | fn | TESTS |
| `sanitize_basename` | fn | TESTS |
| `parse_when` | fn | TESTS |
| `now_unix` | fn | DEAD (no caller in the crate or parity) |
| `render_presence` | fn | TESTS |
| `PollOutcome` | struct | TESTS |
| `read_seen` | fn | TESTS |
| `poll_one` | fn | TESTS |
| `Target` | struct | TESTS |
| `Shown` | struct | TESTS |
| `validate_interval` | fn | TESTS |
| `watch_once` | fn | TESTS |
| `nick_joined` | fn | TESTS |
| `flag_name` | fn | TESTS |
| `render_outcome` | fn | TESTS |
| `EditError` | struct | TESTS |
| `EditRecord` | struct | TESTS |
| `Entry` | struct | TESTS |
| `store_path` | fn | TESTS |
| `MessageStore` | struct | TESTS |
| `MessageStore::new` | method | TESTS |
| `MessageStore::entries` | method | TESTS |
| `MessageStore::get` | method | DEAD (no caller) |
| `MessageStore::append` | method | TESTS |
| `MessageStore::edit` | method | TESTS |

## b25 — messaging extras

| Name | Kind | State |
|---|---|---|
| `announce_key` | fn | TESTS |
| `announce_filter` | fn | TESTS |
| `gate` | fn | TESTS |
| `CONVENTION_WARNING` | const | DEAD (not printed anywhere) |
| `READ_TOOLS` | const | TESTS |
| `WRITE_TOOLS` | const | TESTS |
| `ClipboardError` | struct | DEAD (no function constructs it) |
| `no_tool_msg` | fn | TESTS |
| `parse_edit_text` | fn | TESTS |
| `validate_edit_text` | fn | TESTS |
| `render_kind` | fn | DEAD (no caller) |
| `RenderKind` | enum | DEAD (only `render_kind` returns it) |
| `parse_fwd_text` | fn | TESTS |
| `via_parts` | fn | TESTS |
| `forward_text` | fn | TESTS |
| `verify_clip` | fn | TESTS |
| `short_sha256_hex` | fn | TESTS |
| `SAVE_CAP` | const | TESTS |
| `save_key` | fn | TESTS |
| `room_label` | fn | TESTS |
| `SavedEntry` | struct | TESTS |
| `render_line` | fn | TESTS |
| `filter_room` | fn | TESTS |

## b26 — bridges, digest, admin

| Name | Kind | State |
|---|---|---|
| `MAX_DISPLAY` | const | TESTS |
| `validate_display` | fn | TESTS |
| `validate_rekey_digest` | fn | TESTS |
| `canonical_envelope` | fn | TESTS |
| `PAGE` | const | DEAD (no pagination code) |
| `TOP_N` | const | TESTS |
| `talker_stats` | fn | TESTS |
| `validate_hours` | fn | TESTS |
| `fmt_hour` | fn | DEAD (no caller) |
| `ExportEntry` | struct | TESTS |
| `fmt_time` | fn | TESTS |
| `write_md` | fn | TESTS |
| `write_json_line` | fn | TESTS |
| `uptime_str` | fn | TESTS |
| `health_text` | fn | TESTS |
| `TIMECAPSULE_KEY` | const | DEAD (no sweep code) |
| `REQUEUE_DELAY_SECS` | const | DEAD (no requeue code) |
| `validate_interval` (capsule) | fn | TESTS |
| `is_due` | fn | TESTS |
| `recur_next` | fn | TESTS |
| `MAX_ATTEMPTS` | const | TESTS |
| `BACKOFFS` | const | TESTS |
| `resolve_url` | fn | TESTS |
| `validate_interval` (webhook) | fn | TESTS |
| `payload_for` | fn | TESTS |

## b27 — world packs

| Name | Kind | State |
|---|---|---|
| `T016_FILES`..`T020_FILES` | 5 consts | DEAD (inventory data, no reader) |
| `DEFAULT_INTERVAL_SECONDS` | const | USED |
| `DEFAULT_GRACE_SECONDS` | const | USED |
| `KIND_PAR_CHECK_DUE` | const | USED |
| `KIND_CREW_UNACCOUNTED` | const | USED |
| `SEVERITY_WARNING` | const | USED |
| `SEVERITY_CRITICAL` | const | USED |
| `TL_ENTER` / `TL_COMPLETE` / `TL_EXIT` | 3 consts | USED |
| `CrewRecord` | struct | USED |
| `TimelineEvent` | struct | USED |
| `ParState` | struct | USED |
| `AlertEvent` | struct | USED |
| `validated_crew_id` | fn | USED |
| `new_state` | fn | USED |
| `enter_crew` | fn | USED |
| `complete_par` | fn | USED |
| `exit_crew` | fn | USED |
| `tick` | fn | USED |
| `render_alert` | fn | USED |
| `validate_pack` | fn | USED |
| `pack_dir_matches` | fn | DEAD (no caller, no test) |

## b28–b30 — carried inventories

| Name | Kind | State |
|---|---|---|
| `FILES` (b28) | const | DEAD (no reader) |
| `is_logic_free` (b28) | fn | DEAD (only its own test) |
| `FILES` (b29) | const | DEAD |
| `is_logic_free` (b29) | fn | DEAD (only its own test) |
| `FILES` (b30) | const | DEAD |
| `is_logic_free` (b30) | fn | DEAD (only its own test) |

## Notes

- "USED" is narrow on purpose: only `parity-tests` links the crate, and
  it touches `b27` only. Every other export is exercised solely by unit
  or integration tests in this crate.
- The four `DEAD` groups worth naming for the owner: `now_unix` (the
  clock helper has no caller), `MessageStore::get` (lookup by id is
  unused), `render_kind`/`RenderKind` (the classifier has no caller),
  and `pack_dir_matches` (the directory check is not called by the
  parity test or the crate). None is deleted here; B208 only reports.
